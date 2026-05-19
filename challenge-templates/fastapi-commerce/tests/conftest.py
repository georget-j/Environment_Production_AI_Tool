import pytest

from app.models import store


@pytest.fixture(autouse=True)
def _reset_store():
    store.products.clear()
    store.orders.clear()
    yield
    store.products.clear()
    store.orders.clear()
