from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import json
import uuid
from pathlib import Path
from cart import CartItem


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    quantity: int
    price: float
    currency: str

    @property
    def total_price(self) -> float:
        return self.price * self.quantity


@dataclass
class ShippingAddress:
    first_name: str
    last_name: str
    email: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    postal_code: str
    country: str
    phone: Optional[str] = None


@dataclass
class Order:
    id: str
    paypal_order_id: Optional[str]
    items: List[OrderItem]
    shipping_address: ShippingAddress
    total_amount: float
    currency: str
    status: str  # pending, paid, shipped, delivered, cancelled
    created_at: datetime
    updated_at: datetime
    paypal_transaction_id: Optional[str] = None
    tracking_number: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "paypal_order_id": self.paypal_order_id,
            "items": [vars(item) for item in self.items],
            "shipping_address": vars(self.shipping_address),
            "total_amount": self.total_amount,
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "paypal_transaction_id": self.paypal_transaction_id,
            "tracking_number": self.tracking_number
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Order':
        items = [OrderItem(**item) for item in data["items"]]
        shipping = ShippingAddress(**data["shipping_address"])
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            id=data["id"],
            paypal_order_id=data.get("paypal_order_id"),
            items=items,
            shipping_address=shipping,
            total_amount=data["total_amount"],
            currency=data["currency"],
            status=data["status"],
            created_at=created_at,
            updated_at=updated_at,
            paypal_transaction_id=data.get("paypal_transaction_id"),
            tracking_number=data.get("tracking_number")
        )


class OrderManager:
    def __init__(self):
        self.orders_file = Path("data/orders.json")
        self.orders_file.parent.mkdir(parents=True, exist_ok=True)
        self._orders: Dict[str, Order] = {}
        self._load_orders()

    def _load_orders(self):
        """Load orders from JSON file"""
        if not self.orders_file.exists():
            return

        try:
            with open(self.orders_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for order_data in data:
                    order = Order.from_dict(order_data)
                    self._orders[order.id] = order
        except Exception as e:
            print(f"Error loading orders: {e}")

    def _save_orders(self):
        """Save orders to JSON file"""
        data = [order.to_dict() for order in self._orders.values()]
        with open(self.orders_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_order(self, cart_items: List[CartItem], shipping_address: ShippingAddress) -> Order:
        """Create a new order from cart items"""
        order_id = str(uuid.uuid4())[:8].upper()
        now = datetime.now()

        order_items = []
        total_amount = 0.0
        currency = "EUR"

        for item in cart_items:
            order_item = OrderItem(
                product_id=item.product.id,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.product.price,
                currency=item.product.currency
            )
            order_items.append(order_item)
            total_amount += item.total_price
            currency = item.product.currency

        order = Order(
            id=order_id,
            paypal_order_id=None,
            items=order_items,
            shipping_address=shipping_address,
            total_amount=total_amount,
            currency=currency,
            status="pending",
            created_at=now,
            updated_at=now
        )

        self._orders[order_id] = order
        self._save_orders()
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)

    def update_order_status(self, order_id: str, status: str, paypal_transaction_id: Optional[str] = None):
        """Update order status"""
        order = self._orders.get(order_id)
        if order:
            order.status = status
            order.updated_at = datetime.now()
            if paypal_transaction_id:
                order.paypal_transaction_id = paypal_transaction_id
            self._save_orders()

    def set_paypal_order_id(self, order_id: str, paypal_order_id: str):
        """Set PayPal order ID for an order"""
        order = self._orders.get(order_id)
        if order:
            order.paypal_order_id = paypal_order_id
            order.updated_at = datetime.now()
            self._save_orders()

    def add_tracking_number(self, order_id: str, tracking_number: str):
        """Add tracking number to order"""
        order = self._orders.get(order_id)
        if order:
            order.tracking_number = tracking_number
            order.status = "shipped"
            order.updated_at = datetime.now()
            self._save_orders()

    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        return list(self._orders.values())

    def get_orders_by_status(self, status: str) -> List[Order]:
        """Get orders by status"""
        return [order for order in self._orders.values() if order.status == status]

    def get_recent_orders(self, limit: int = 10) -> List[Order]:
        """Get recent orders"""
        sorted_orders = sorted(self._orders.values(), key=lambda x: x.created_at, reverse=True)
        return sorted_orders[:limit]


# Global order manager instance
order_manager = OrderManager()