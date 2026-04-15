from datamodel import OrderDepth, TradingState, Order
from typing import Dict
import json
import numpy as np

class Trader:

    POSITION_LIMITS = {
        "ASH_COATED_OSMIUM": 80,
        "INTARIAN_PEPPER_ROOT": 80,
    }

    # --- toggles ---
    USE_EWMA = False # set True to test EWMA
    EWMA_ALPHA = 0.25 # much slower than the broken 0.54
    Z_WINDOW = 60
    Z_ENTRY = 1.0
    MAX_Z = 2.0
    EDGE_THRESHOLD = 0.1
    MICROPRICE_ALPHA = 4.0
    MM_BASE = 13
    MM_MAX_EXTRA = 5
    MAX_HISTORY = 300
    BASE_FAIR = 10000.0
    VOL_STD_CUTOFF = 8.0 # round 1 never hits this

    def microprice(self, best_bid, best_ask, bid_vol, ask_vol):
        denom = bid_vol + ask_vol
        if denom == 0:
            return (best_bid + best_ask) / 2
        return (best_bid * ask_vol + best_ask * bid_vol) / denom

    def get_prices(self, od: OrderDepth):
        if not od.buy_orders or not od.sell_orders:
            return None
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        bid_vol = od.buy_orders[best_bid]
        ask_vol = -od.sell_orders[best_ask]
        return best_bid, best_ask, bid_vol, ask_vol

    def latency_aware_quotes(self, best_bid, best_ask, bid_vol, ask_vol):
        mp = self.microprice(best_bid, best_ask, bid_vol, ask_vol)
        mid = (best_bid + best_ask) / 2
        edge = mp - mid
        if edge > self.EDGE_THRESHOLD:
            return best_ask, best_ask
        if edge < -self.EDGE_THRESHOLD:
            return best_bid, best_bid
        if best_ask - best_bid > 1:
            return best_bid + 1, best_ask - 1
        return best_bid, best_ask

    def trade_osmium(self, od: OrderDepth, position: int, hist: Dict):
        prices = self.get_prices(od)
        if not prices:
            return [], hist
        best_bid, best_ask, bid_vol, ask_vol = prices
        mid = (best_bid + best_ask) / 2.0

        # history
        p = hist.get("prices", [])
        ema = hist.get("ema", mid)
        p.append(mid)
        p = p[-self.MAX_HISTORY:]

        # mean
        if self.USE_EWMA:
            ema = self.EWMA_ALPHA * mid + (1 - self.EWMA_ALPHA) * ema
            mean = 0.8 * ema + 0.2 * self.BASE_FAIR
        else:
            mean = np.mean(p[-self.Z_WINDOW:]) if len(p) >= self.Z_WINDOW else self.BASE_FAIR

        std = float(np.std(p[-self.Z_WINDOW:])) if len(p) >= self.Z_WINDOW else 5.0
        z = (mid - mean) / max(std, 1.0)

        mp = self.microprice(best_bid, best_ask, bid_vol, ask_vol)
        edge = mp - mid
        signal = z + self.MICROPRICE_ALPHA * edge

        # sizing
        vol_mult = 0.7 if std > self.VOL_STD_CUTOFF else 1.0
        prop_size = self.MM_BASE + int(self.MM_MAX_EXTRA * min(abs(signal), 1.0))
        if best_ask - best_bid > 2:
            prop_size += 3
        mm_size = max(5, int(prop_size * vol_mult))

        # quotes with gentle skew
        buy_px, sell_px = self.latency_aware_quotes(best_bid, best_ask, bid_vol, ask_vol)
        skew = int(position / 30) # was /20 in broken version
        buy_px -= max(0, skew)
        sell_px -= min(0, skew)

        # keep from crossing
        buy_px = min(buy_px, best_ask - 1)
        sell_px = max(sell_px, best_bid + 1)

        limit = self.POSITION_LIMITS["ASH_COATED_OSMIUM"]
        orders = []

        if abs(signal) < self.Z_ENTRY:
            if position < limit:
                qty = min(mm_size, limit - position)
                orders.append(Order("ASH_COATED_OSMIUM", buy_px, qty))
            if position > -limit:
                qty = min(mm_size, position + limit)
                orders.append(Order("ASH_COATED_OSMIUM", sell_px, -qty))
        else:
            target_frac = np.clip(-signal / self.MAX_Z, -1, 1)
            target_pos = int(target_frac * limit * vol_mult)
            delta = target_pos - position
            if delta > 0:
                qty = min(delta, limit - position)
                orders.append(Order("ASH_COATED_OSMIUM", buy_px, qty))
            elif delta < 0:
                qty = min(-delta, position + limit)
                orders.append(Order("ASH_COATED_OSMIUM", sell_px, -qty))

        return orders, {"prices": p, "ema": ema}

    def trade_pepper(self, od: OrderDepth, position: int):
        # back to your original – no ceiling
        orders = []
        if not od.sell_orders:
            return orders
        best_ask = min(od.sell_orders.keys())
        limit = self.POSITION_LIMITS["INTARIAN_PEPPER_ROOT"]
        if position < limit:
            orders.append(Order("INTARIAN_PEPPER_ROOT", best_ask, limit - position))
        return orders

    def run(self, state: TradingState):
        data = json.loads(state.traderData) if state.traderData else {}
        result = {}
        for prod, od in state.order_depths.items():
            pos = state.position.get(prod, 0)
            hist = data.get(prod, {})
            if prod == "ASH_COATED_OSMIUM":
                orders, new_hist = self.trade_osmium(od, pos, hist)
                data[prod] = new_hist
                result[prod] = orders
            elif prod == "INTARIAN_PEPPER_ROOT":
                result[prod] = self.trade_pepper(od, pos)
            else:
                result[prod] = []
        return result, 0, json.dumps(data)