def add_item(name, price, cart=[]):
    """Add an item to a cart and return the cart. Starts a new cart if none is given."""
    cart.append({"name": name, "price": price})
    return cart


def cart_total(cart, discount_percent=0):
    """Total price after a percentage discount, e.g. 10 means 10% off."""
    total = sum(item["price"] for item in cart)
    return total - discount_percent
