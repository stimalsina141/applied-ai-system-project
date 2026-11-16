def add_item(name, price, cart=None):
    """Add an item to a cart and return the cart. Starts a new cart if none is given."""
    if cart is None:
        cart = []
    cart.append({"name": name, "price": price})
    return cart


def cart_total(cart, discount_percent=0):
    """Total price after a percentage discount, e.g. 10 means 10% off."""
    total = sum(item["price"] for item in cart)
    return total * (1 - discount_percent / 100)
