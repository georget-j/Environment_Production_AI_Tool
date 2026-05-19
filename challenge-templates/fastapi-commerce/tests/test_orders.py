import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import store
from app.orders import compute_total, create_order


@pytest.fixture
def seeded_products():
    p1 = store.add_product("Notebook", 1200)
    p2 = store.add_product("Coffee mug", 950)
    return p1, p2


def test_compute_total_without_coupon(seeded_products) -> None:
    p1, p2 = seeded_products
    total = compute_total([(p1.id, 2), (p2.id, 1)], coupon_code=None)
    # 2 * 1200 + 1 * 950 = 3350
    assert total == 3350


def test_compute_total_with_valid_coupon(seeded_products) -> None:
    p1, _ = seeded_products
    total = compute_total([(p1.id, 1)], coupon_code="WELCOME10")
    # 10% off 1200 = 1080
    assert total == 1080


def test_compute_total_create_order_persists_total(seeded_products) -> None:
    p1, p2 = seeded_products
    order = create_order([(p1.id, 1), (p2.id, 2)], coupon_code=None)
    # 1200 + 2*950 = 3100
    assert order.total_cents == 3100
    assert store.orders[order.id].total_cents == 3100


def test_invalid_quantity_rejected(seeded_products) -> None:
    p1, _ = seeded_products
    with pytest.raises(ValueError):
        compute_total([(p1.id, 0)])


def test_orders_endpoint_smoke(seeded_products) -> None:
    p1, _ = seeded_products
    client = TestClient(app)
    response = client.post(
        "/orders",
        json={"items": [{"product_id": str(p1.id), "quantity": 1}], "coupon_code": None},
    )
    assert response.status_code == 200
    assert response.json()["total_cents"] == 1200
