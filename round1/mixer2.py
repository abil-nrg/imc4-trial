from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import json
import numpy as np

class Trader:

    POSITION_LIMITS = {
        "ASH_COATED_OSMIUM": 80,
        "INTARIAN_PEPPER_ROOT": 80,
    }

    Z_WINDOW = 50
    Z_ENTRY = 3
    MAX_Z = 2.0
    EDGE_THRESHOLD = 0.1
    MICROPRICE_ALPHA = 4.0
    MM_SIZE = 20
    MAX_HISTORY = 300
    VOL_STD_CUTOFF = 8.0 

    def compute_zscore(self, prices: List[float]):
        if len(prices) < self.Z_WINDOW:
            return 0.0
        arr = np.array(prices[-self.Z_WINDOW:])
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-8:
            return 0.0
        return float((arr[-1] - mean) / std)

    def microprice(self, best_bid, best_ask, bid_vol, ask_vol):
        denom = bid_vol + ask_vol
        if denom == 0:
            return (best_bid + best_ask) / 2
        return (best_bid * ask_vol + best_ask * bid_vol) / denom

    def get_prices(self, order_depth: OrderDepth):
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        bid_vol = order_depth.buy_orders[best_bid]
        ask_vol = -order_depth.sell_orders[best_ask]
        return best_bid, best_ask, bid_vol, ask_vol

    def latency_aware_quotes(self, best_bid, best_ask, bid_vol, ask_vol):
        mid = (best_bid + best_ask) / 2
        mp = self.microprice(best_bid, best_ask, bid_vol, ask_vol)
        edge = mp - mid

        if edge > self.EDGE_THRESHOLD:
            return best_ask, best_ask
        elif edge < -self.EDGE_THRESHOLD:
            return best_bid, best_bid
        else:
            if best_ask - best_bid > 1:
                return best_bid + 1, best_ask - 1
            else:
                return best_bid, best_ask

    def trade_osmium(self, order_depth: OrderDepth, position: int, history: List[float]):
        orders = []
        prices = self.get_prices(order_depth)
        if prices is None:
            return orders
        best_bid, best_ask, bid_vol, ask_vol = prices
        mid = (best_bid + best_ask) / 2

        history.append(mid)
        history[:] = history[-self.MAX_HISTORY:]

        z = self.compute_zscore(history)
        mp = self.microprice(best_bid, best_ask, bid_vol, ask_vol)
        edge = mp - mid
        signal = z + self.MICROPRICE_ALPHA * edge

        # volatility filter - matches your half-life spikes
        if len(history) >= self.Z_WINDOW:
            std = float(np.std(history[-self.Z_WINDOW:]))
        else:
            std = 5.0
        vol_mult = 0.5 if std > self.VOL_STD_CUTOFF else 1.0

        limit = self.POSITION_LIMITS["ASH_COATED_OSMIUM"]
        buy_price, sell_price = self.latency_aware_quotes(best_bid, best_ask, bid_vol, ask_vol)

        if abs(signal) < self.Z_ENTRY:
            # size up when spread is wide, size down when volatile
            mm_size = self.MM_SIZE + (5 if (best_ask - best_bid) > 2 else 0)
            mm_size = int(mm_size * vol_mult)
            mm_size = max(5, mm_size)

            if position < limit:
                qty = min(mm_size, limit - position)
                orders.append(Order("ASH_COATED_OSMIUM", buy_price, qty))
            if position > -limit:
                qty = min(mm_size, position + limit)
                orders.append(Order("ASH_COATED_OSMIUM", sell_price, -qty))
            return orders

        target_frac = np.clip(-signal / self.MAX_Z, -1, 1)
        target_pos = int(target_frac * limit * vol_mult)
        delta = target_pos - position

        if delta > 0:
            qty = min(delta, limit - position)
            if qty > 0:
                orders.append(Order("ASH_COATED_OSMIUM", buy_price, qty))
        elif delta < 0:
            qty = min(-delta, position + limit)
            if qty > 0:
                orders.append(Order("ASH_COATED_OSMIUM", sell_price, -qty))
        return orders

    def trade_pepper(self, order_depth: OrderDepth, position: int):
        orders = []
        if not order_depth.sell_orders:
            return orders
        best_ask = min(order_depth.sell_orders.keys())
        limit = self.POSITION_LIMITS["INTARIAN_PEPPER_ROOT"]
        if position < limit:
            qty = limit - position
            orders.append(Order("INTARIAN_PEPPER_ROOT", best_ask, qty))
        return orders

    def run(self, state: TradingState):
        if state.traderData:
            data = json.loads(state.traderData)
        else:
            data = {"history": {}}
        result = {}
        for product, order_depth in state.order_depths.items():
            position = state.position.get(product, 0)
            if product not in data["history"]:
                data["history"][product] = []
            if product == "ASH_COATED_OSMIUM":
                orders = self.trade_osmium(order_depth, position, data["history"][product])
            elif product == "INTARIAN_PEPPER_ROOT":
                orders = self.trade_pepper(order_depth, position)
            else:
                orders = []
            result[product] = orders
        traderData = json.dumps(data)
        conversions = 0
        return result, conversions, traderData