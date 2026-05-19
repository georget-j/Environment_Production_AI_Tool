from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.models import seed, store
from app.orders import create_order

app = FastAPI(title="fastapi-commerce", version="0.0.0")
seed()


class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn]
    coupon_code: str | None = None


class OrderOut(BaseModel):
    id: UUID
    total_cents: int
    coupon_code: str | None


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products")
def list_products() -> list[dict]:
    return [
        {"id": str(p.id), "name": p.name, "price_cents": p.price_cents}
        for p in store.products.values()
    ]


@app.post("/orders", response_model=OrderOut)
def post_order(body: OrderCreate) -> OrderOut:
    try:
        order = create_order([(i.product_id, i.quantity) for i in body.items], body.coupon_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrderOut(id=order.id, total_cents=order.total_cents, coupon_code=order.coupon_code)
