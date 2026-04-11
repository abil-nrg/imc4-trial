"""
trader.py
Defines the central trader class
began with the default template on https://imc-prosperity.notion.site/writing-an-algorithm-in-python
"""

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Any
import string
import json
import numpy as np

class Trader:

    def bid(self): 
        """
        For ROUND 2 ONLY
        """
        return 15
    
    #=======GENERATE HISTORIC STATS=============
    def generate_analytics(self, product : str, history_dict : Dict[str, List[float]], window : int) -> Dict[str, Any]:
        """
        Transforms raw order book history, turns into a statistical report
        """
        prices = history_dict.get(product, [])

        report = {
            "vol": 0.0,
            "mean_price" : 0.0,
            "momentum" : 0.0,
        }
        if not prices:
            return report
        
        if len(prices) == 1:
            report["mean_price"] = prices[0]
            return report
        
        price_arr = np.array(prices)[-window:]

        log_returns = np.diff(np.log(price_arr))
        vol = np.std(log_returns) if len(log_returns) > 0 else 0.0

        report["vol"] = float(vol)
        report["mean_price"] = np.mean(price_arr) 
        report["momentum"] = 0 #later

        return report
    
    #=======MAIN LOOP===============================
    def run(self, state: TradingState):
        """Takes all buy and sell orders for all
        symbols as an input, and outputs a list of orders to be sent."""
        
        #Load in history
        if state.traderData:
            data = json.loads(state.traderData)
        else:
            data = {"history": {}}
        
        result = {}
        conversions = 0
        POSITION_LIMITS = {
            "EMERALDS": 80,
            "TOMATOES": 80
        }
        POS_DEFAULT = 80
        WINDOW_SIZE = 100
        
        #look thru order book
        for product in state.order_depths:
            print(f"Product:{product}")
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            #update histroy
            if product not in data["history"]:
                data["history"][product] = []
            sell_orders = sorted(order_depth.sell_orders.items())
            buy_orders = sorted(order_depth.buy_orders.items())

            if sell_orders and buy_orders:
                best_ask, _ = sell_orders[0]
                best_bid, _ = buy_orders[0]
                mid_price = (best_ask + best_bid)/2

                data["history"][product].append(mid_price)
            else:
                continue #history isnt updated! avoid div by 0
            
            #generate the statistics
            stats = self.generate_analytics(product, data["history"], WINDOW_SIZE)
            
            #figure out current conditions
            current_vol = stats["vol"]
            current_mean = stats["mean_price"]

            if current_mean == 0:
                continue
            
            current_pos = state.position.get(product, 0)
            limit = POSITION_LIMITS.get(product, POS_DEFAULT)

            edge = max(1, current_vol * mid_price)
            acceptable_buy = current_mean - edge
            acceptable_sell = current_mean + edge

            #======BUY =====
            sorted_asks = sorted(order_depth.sell_orders.items())
            for ask, amount in sorted_asks:
                if ask < acceptable_buy and current_pos < limit:
                    buy_qty = min(-amount, limit - current_pos)
                    if buy_qty > 0:
                        print(f"BUY {product} | Qty : {buy_qty} | Price : {ask}")
                        orders.append(Order(product, ask, buy_qty))
                        current_pos += buy_qty

            #=======SELL ====
            sorted_bids = sorted(order_depth.buy_orders.items())
            for bid, amount in sorted_bids:
                if bid > acceptable_sell and current_pos > -limit:
                    sell_qty = min(amount, current_pos + limit)
                    if sell_qty > 0:
                        print(f"SELL {product} | Qty : {sell_qty} | Price : {bid}")
                        orders.append(Order(product, bid, -sell_qty))
                        current_pos -= sell_qty
        
            result[product] = orders
    
        traderData = json.dumps(data)
        
        return result, conversions, traderData

    #=========ANALYTICS HELPERS=================================


