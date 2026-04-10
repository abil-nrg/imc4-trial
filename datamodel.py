from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Order:
    symbol: str
    price: int
    quantity: int

    @property
    def product(self) -> str:
        return self.symbol


@dataclass
class OrderDepth:
    buy_orders: Dict[int, int] = field(default_factory=dict)
    sell_orders: Dict[int, int] = field(default_factory=dict)


@dataclass
class TradingState:
    timestamp: int
    order_depths: Dict[str, OrderDepth]
    position: Dict[str, int]
    traderData: str = ""