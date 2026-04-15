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
        """Standard rolling SMA detrending."""
        if len(prices) < window:
            return np.zeros_like(prices)
        
        # Calculate rolling mean using cumsum for speed
        cumsum = np.cumsum(prices)
        sma = (cumsum[window:] - cumsum[:-window]) / window
        
        residuals = prices[window:] - sma
        return residuals

    def generate_analytics(self, product, history_dict, window, lag=1):
        """
        Compute analytics on detrended price series.
        Autocorr is now calculated on the returns (differences) of residuals.
        """
        prices = history_dict.get(product, [])
        report = {
            "zscore": 0.0,
            "std": 0.0,
            "autocorr": 0.0,
            "trend_slope": 0.0,
        }

        if len(prices) < window + lag + 1: # Added +1 for return calculation
            return report

        price_arr = np.array(prices[-(window * 2):])
        
        # ----- Detrend based on product -----
        if product == "ASH_COATED_OSMIUM":
            residuals = self.detrend_sma(price_arr, window)
        else:
            residuals = self.detrend_linear(price_arr)

        # Statistics on residuals for Z-score
        mean_resid = np.mean(residuals)
        std_resid = np.std(residuals)
        z = (residuals[-1] - mean_resid) / std_resid if std_resid > 1e-8 else 0.0

        # ----- Autocorrelation of Residual RETURNS -----
        res_returns = np.diff(residuals)

        if len(res_returns) > lag:
            r_t = res_returns[:-lag]
            r_lagged = res_returns[lag:]
            
            if np.std(r_t) > 1e-8 and np.std(r_lagged) > 1e-8:
                # Correlation between return at T and return at T-lag
                autocorr = np.corrcoef(r_t, r_lagged)[0, 1]
            else:
                autocorr = 0.0
        else:
            autocorr = 0.0

        report["zscore"] = float(z)
        report["std"] = float(std_resid)
        report["autocorr"] = float(autocorr)
        report["trend_slope"] = float(np.polyfit(np.arange(len(price_arr)), price_arr, 1)[0])

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
            "ASH_COATED_OSMIUM": 80,
            "INTARIAN_PEPPER_ROOT": 80,
        }
        POS_DEFAULT = 80
        WINDOW_SIZE = 250
        MAX_HISTORY = 1000

        Z_ENTRY = 0
        MAX_SPREAD = 100
        MAX_EXPECTED_Z = 2
        
        PEPPER_BUY_AND_HOLD = True 

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

            # ===== BUY AND HOLD BYPASS =====
            if product == "INTARIAN_PEPPER_ROOT" and PEPPER_BUY_AND_HOLD:
                current_pos = state.position.get(product, 0)
                limit = POSITION_LIMITS.get(product, POS_DEFAULT)
                
                if current_pos < limit:
                    buy_qty = limit - current_pos
                    orders.append(Order(product, int(best_ask), int(buy_qty)))
                    
                result[product] = orders
                continue  # Skip all analytics and mean-reversion logic for this product

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

            if spread > MAX_SPREAD:          # Spread filter
                result[product] = orders
                print(f"spread no {spread}")
                continue

            if abs(z) < Z_ENTRY:             # Weak signal
                result[product] = orders
                print(f"z no {z}")
                continue

            # Mean reversion must exist on detrended residuals 
            if autocorr > -0.1:
                result[product] = orders
                print(f"auto no {autocorr}")
                continue

            # ===== POSITION SIZING =====
            # Map Z‑score linearly to a fraction of the limit, capped at ±limit
            target_frac = np.clip(z / MAX_EXPECTED_Z, -1.0, 1.0)
            target_pos = int(-target_frac * limit)
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