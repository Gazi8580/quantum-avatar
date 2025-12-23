from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
from products import Product, catalog


@dataclass
class CartItem:
    product: Product
    quantity: int

    @property
    def total_price(self) -> float:
        return self.product.price * self.quantity


class ShoppingCart:
    def __init__(self):
        if "cart" not in st.session_state:
            st.session_state.cart = {}
        self._cart: Dict[str, CartItem] = st.session_state.cart

    def add_item(self, product_id: str, quantity: int = 1) -> bool:
        """Add item to cart. Returns True if successful."""
        product = catalog.get_product_by_id(product_id)
        if not product:
            return False

        if product_id in self._cart:
            new_quantity = self._cart[product_id].quantity + quantity
            if new_quantity > product.stock:
                return False
            self._cart[product_id].quantity = new_quantity
        else:
            if quantity > product.stock:
                return False
            self._cart[product_id] = CartItem(product, quantity)

        st.session_state.cart = self._cart
        return True

    def remove_item(self, product_id: str):
        """Remove item from cart"""
        if product_id in self._cart:
            del self._cart[product_id]
            st.session_state.cart = self._cart

    def update_quantity(self, product_id: str, quantity: int) -> bool:
        """Update item quantity. Returns True if successful."""
        if product_id not in self._cart:
            return False

        product = self._cart[product_id].product
        if quantity <= 0:
            self.remove_item(product_id)
            return True

        if quantity > product.stock:
            return False

        self._cart[product_id].quantity = quantity
        st.session_state.cart = self._cart
        return True

    def get_items(self) -> List[CartItem]:
        """Get all cart items"""
        return list(self._cart.values())

    def get_item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self._cart.values())

    def get_total_price(self) -> float:
        """Get total price of all items"""
        return sum(item.total_price for item in self._cart.values())

    def clear_cart(self):
        """Clear all items from cart"""
        self._cart.clear()
        st.session_state.cart = self._cart

    def is_empty(self) -> bool:
        """Check if cart is empty"""
        return len(self._cart) == 0

    def get_cart_summary(self) -> Dict:
        """Get cart summary information"""
        items = self.get_items()
        total_items = self.get_item_count()
        total_price = self.get_total_price()

        return {
            "items": items,
            "total_items": total_items,
            "total_price": total_price,
            "currency": items[0].product.currency if items else "EUR"
        }


# Global cart instance
cart = ShoppingCart()