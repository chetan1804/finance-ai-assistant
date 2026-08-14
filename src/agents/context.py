from datetime import date


ALLOWED_INTENTS = {
    "expense",
    "income",
    "category_expense",
    "balance",
    "unknown",
}


def _iso_date_or_none(value):
    if not value or value.upper() == "NONE":
        return None

    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def parse_context(text: str) -> dict:
    """Parse and validate the small text protocol returned by the LLM."""
    values = {}

    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue

        key, value = raw_line.strip().split(":", 1)
        values[key.strip().upper()] = value.strip()

    intent = values.get("INTENT", "unknown").lower()
    if intent not in ALLOWED_INTENTS:
        intent = "unknown"

    category = values.get("CATEGORY")
    if not category or category.upper() == "NONE":
        category = None

    start_date = _iso_date_or_none(values.get("START_DATE"))
    end_date = _iso_date_or_none(values.get("END_DATE"))

    if start_date and end_date and start_date > end_date:
        start_date = None
        end_date = None

    resolved_query = values.get("RESOLVED_QUERY")
    if not resolved_query or resolved_query.upper() == "NONE":
        resolved_query = None

    return {
        "intent": intent,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "resolved_query": resolved_query,
    }
