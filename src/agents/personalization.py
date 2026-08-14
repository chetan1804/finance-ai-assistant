CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}


def _group_indian_digits(digits: str) -> str:
    if len(digits) <= 3:
        return digits

    head = digits[:-3]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return f"{','.join(groups)},{digits[-3:]}"


def format_money(amount, currency="INR") -> str:
    """Format a numeric database result for the user's display currency."""
    numeric = float(amount)
    sign = "-" if numeric < 0 else ""
    whole, fraction = f"{abs(numeric):.2f}".split(".")

    if currency.upper() == "INR":
        whole = _group_indian_digits(whole)
    else:
        whole = f"{int(whole):,}"

    decimals = "" if fraction == "00" else f".{fraction.rstrip('0')}"
    symbol = CURRENCY_SYMBOLS.get(currency.upper(), f"{currency.upper()} ")
    return f"{sign}{symbol}{whole}{decimals}"
