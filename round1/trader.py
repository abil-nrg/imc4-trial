"""
trader.py
Improved Z-score mean reversion with:
- detrending (linear trend OR moving average, product-specific)
- position scaling
- passive execution
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict, Any
import json
import numpy as np


class Trader:

    # ======== ANALYTICS =========
    def fit_trend(self, prices: np.ndarray) -> tuple:
        """Fit linear trend to price array."""
        t = np.arange(len(prices))
        slope, intercept = np.polyfit(t, prices, 1)
        return slope, intercept

    def detrend_linear(self, prices: np.ndarray) -> np.ndarray:
        """Subtract best‑fit straight line."""
        slope, intercept = self.fit_trend(prices)
        t = np.arange(len(prices))
        trend_line = slope * t + intercept
        return prices - trend_line

    def detrend_sma(self, prices: np.ndarray, window: int) -> np.ndarray:
        """
        Subtract a simple moving average (SMA) of the given window length.
        For each index i, residual[i] = price[i] - SMA(price[max(0,i-window+1):i+1]).
        For i < window-1, SMA is the expanding mean of all prices up to i.
        """
        residuals = np.zeros_like(prices)
        for i in range(len(prices)):
            start = max(0, i - window + 1)
            sma = np.mean(prices[start:i+1])
            residuals[i] = prices[i] - sma
        return residuals

    def generate_analytics(self, product, history_dict, window, lag=1):
        """
        Compute analytics on detrended price series.
        For product 'ASH' (ASH_COATED_OSMIUM): remove SMA (window length = window).
        For others: remove linear trend.
        Returns z‑score, standard deviation of residuals, autocorrelation of residuals,
        and the raw trend slope (for reference only, not used as a filter).
        """
        prices = history_dict.get(product, [])
        report = {
            "zscore": 0.0,
            "std": 0.0,
            "autocorr": 0.0,
            "trend_slope": 0.0,
        }

        if len(prices) < window + lag:
            return report

        price_arr = np.array(prices[-window:])
        t = np.arange(len(price_arr))

        # ----- Detrend based on product -----
        if product == "ASH_COATED_OSMIUM":
            # Proper SMA detrending (fixes problem #1)
            residuals = self.detrend_sma(price_arr, window)
        else:
            # Linear detrending
            residuals = self.detrend_linear(price_arr)

        # Statistics on residuals
        mean_resid = np.mean(residuals)
        std_resid = np.std(residuals)

        if std_resid > 1e-8:
            z = (residuals[-1] - mean_resid) / std_resid
        else:
            z = 0.0

        # ----- Autocorrelation of residuals (fixes problem #3) -----
        if len(residuals) > lag:
            r1 = residuals[:-lag]
            r2 = residuals[lag:]
            if np.std(r1) > 1e-8 and np.std(r2) > 1e-8:
                autocorr = np.corrcoef(r1, r2)[0, 1]
            else:
                autocorr = 0.0
        else:
            autocorr = 0.0

        # ----- Raw trend slope (kept for logging, not used as filter) -----
        slope = np.polyfit(t, price_arr, 1)[0]

        report["zscore"] = float(z)
        report["std"] = float(std_resid)
        report["autocorr"] = float(autocorr)
        report["trend_slope"] = float(slope)

        return report

    # ======== MAIN LOOP =========
    def run(self, state: TradingState):

        # ===== LOAD DATA =====
        if state.traderData:
            data = json.loads(state.traderData)
        else:
            data = {"history": {}}

        result = {}
        conversions = 0

        # ===== PARAMS =====
        POSITION_LIMITS = {
            "EMERALDS": 80,
            "TOMATOES": 80,
            "ASH": 80,
            "PEPPER": 80,
        }
        POS_DEFAULT = 80
        WINDOW_SIZE = 500
        MAX_HISTORY = 1000

        Z_ENTRY = 1.0
        MAX_SPREAD = 20
        MAX_EXPECTED_Z = 2.0

        # ===== LOOP PRODUCTS =====
        for product in state.order_depths:

            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            # init history
            if product not in data["history"]:
                data["history"][product] = []

            sell_orders = sorted(order_depth.sell_orders.items())
            buy_orders = sorted(order_depth.buy_orders.items())

            if not sell_orders or not buy_orders:
                result[product] = orders
                continue

            best_ask, ask_vol = sell_orders[0]
            best_bid, bid_vol = buy_orders[0]
            mid_price = (best_ask + best_bid) / 2

            # ===== UPDATE HISTORY =====
            data["history"][product].append(mid_price)
            data["history"][product] = data["history"][product][-MAX_HISTORY:]

            # ===== ANALYTICS (detrended Z‑score) =====
            stats = self.generate_analytics(product, data["history"], WINDOW_SIZE)
            z = stats["zscore"]
            autocorr = stats["autocorr"]
            std = stats["std"]

            current_pos = state.position.get(product, 0)
            limit = POSITION_LIMITS.get(product, POS_DEFAULT)
            spread = best_ask - best_bid

            # ===== FILTERS =====
            if std == 0:                     # Not enough data
                result[product] = orders
                continue

            if spread > MAX_SPREAD:          # Spread filter
                result[product] = orders
                continue

            if abs(z) < Z_ENTRY:             # Weak signal
                result[product] = orders
                continue

            # Mean reversion must exist on detrended residuals 
            if autocorr > -0.1:
                result[product] = orders
                continue

            # ===== POSITION SIZING =====
            # Map Z‑score linearly to a fraction of the limit, capped at ±limit
            target_frac = np.clip(z / MAX_EXPECTED_Z, -1.0, 1.0)
            target_pos = int(target_frac * limit)
            delta = target_pos - current_pos

            # ===== PASSIVE PRICES =====
            if spread > 1:
                buy_price = best_bid + 1
                sell_price = best_ask - 1
            else:
                # Spread == 1: join the respective queue
                buy_price = best_bid
                sell_price = best_ask

            # ===== EXECUTION =====
            if delta > 0:
                buy_qty = min(delta, limit - current_pos)
                if buy_qty > 0:
                    orders.append(Order(product, int(buy_price), int(buy_qty)))
            elif delta < 0:
                sell_qty = min(-delta, current_pos + limit)
                if sell_qty > 0:
                    orders.append(Order(product, int(sell_price), int(-sell_qty)))

            result[product] = orders

        traderData = json.dumps(data)
        return result, conversions, traderData