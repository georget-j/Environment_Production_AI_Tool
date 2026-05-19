"""In-memory data store. Module 4 of the track introduces a real DB."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Product:
    id: UUID
    name: str
    price_cents: int


@dataclass
class Order:
    id: UUID
    items: list[tuple[UUID, int]]  # (product_id, quantity)
    coupon_code: str | None
    total_cents: int


@dataclass
class _Store:
    products: dict[UUID, Product] = field(default_factory=dict)
    orders: dict[UUID, Order] = field(default_factory=dict)

    def add_product(self, name: str, price_cents: int) -> Product:
        product = Product(id=uuid4(), name=name, price_cents=price_cents)
        self.products[product.id] = product
        return product

    def get_product(self, product_id: UUID) -> Product | None:
        return self.products.get(product_id)

    def add_order(self, order: Order) -> None:
        self.orders[order.id] = order

    def list_orders(self) -> Iterator[Order]:
        yield from self.orders.values()


store = _Store()


def seed() -> None:
    """Idempotent seed for tests / local dev."""
    if store.products:
        return
    store.add_product("Notebook", 1200)
    store.add_product("Mechanical keyboard", 9900)
    store.add_product("Coffee mug", 950)
