def execute_finance_query(service, user_id: int, context: dict):
    """Execute a validated finance context against a user-scoped service."""
    common = {
        "user_id": user_id,
        "start_date": context.get("start_date"),
        "end_date": context.get("end_date"),
    }
    intent = context.get("intent")
    category = context.get("category")

    if intent == "category_expense" and category:
        return service.get_category_expenses(category=category, **common)
    if intent == "expense":
        return service.get_total_expenses(**common)
    if intent == "income":
        return service.get_total_income(**common)
    if intent == "balance":
        return service.get_savings(**common)
    return None
