import pytest

from cart import add_item, cart_total


def test_each_new_cart_starts_empty():
    first = add_item("apple", 1.0)
    second = add_item("bread", 3.0)
    assert first == [{"name": "apple", "price": 1.0}]
    assert second == [{"name": "bread", "price": 3.0}]


def test_add_to_existing_cart():
    cart = add_item("apple", 1.0, [])
    add_item("milk", 2.5, cart)
    assert len(cart) == 2


def test_total_without_discount():
    cart = [{"name": "a", "price": 20.0}, {"name": "b", "price": 30.0}]
    assert cart_total(cart) == pytest.approx(50.0)


def test_total_with_percentage_discount():
    cart = [{"name": "a", "price": 200.0}]
    assert cart_total(cart, discount_percent=10) == pytest.approx(180.0)
