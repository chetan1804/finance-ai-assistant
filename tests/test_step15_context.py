from src.agents.context import parse_context
from src.agents.personalization import format_money


def test_parse_context_accepts_valid_personalized_query():
    result = parse_context(
        """
        INTENT: category_expense
        CATEGORY: Food
        START_DATE: 2026-07-01
        END_DATE: 2026-07-31
        RESOLVED_QUERY: How much did I spend on food last month?
        """
    )

    assert result == {
        "intent": "category_expense",
        "category": "Food",
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
        "resolved_query": "How much did I spend on food last month?",
    }


def test_parse_context_rejects_unknown_values_and_reversed_dates():
    result = parse_context(
        """
        INTENT: prediction
        CATEGORY: NONE
        START_DATE: 2026-08-31
        END_DATE: 2026-08-01
        RESOLVED_QUERY: NONE
        """
    )

    assert result["intent"] == "unknown"
    assert result["category"] is None
    assert result["start_date"] is None
    assert result["end_date"] is None
    assert result["resolved_query"] is None


def test_personalized_currency_formatting():
    assert format_money(20000, "INR") == "₹20,000"
    assert format_money(125000.5, "INR") == "₹1,25,000.5"
    assert format_money(-1200, "USD") == "-$1,200"


def test_parse_context_accepts_loan_and_investment_intents():
    loan = parse_context(
        "INTENT: loan_emi\nCATEGORY: home\nSTART_DATE: NONE\nEND_DATE: NONE"
    )
    investment = parse_context(
        "INTENT: investment\nCATEGORY: NONE\nSTART_DATE: NONE\nEND_DATE: NONE"
    )

    assert loan["intent"] == "loan_emi"
    assert loan["category"] == "home"
    assert investment["intent"] == "investment"
