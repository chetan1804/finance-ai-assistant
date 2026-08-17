from src.agents.query import execute_finance_query


class QueryService:
    def get_total_loan_emi(self, **kwargs):
        assert kwargs == {
            "user_id": 7,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "loan_type": "home",
        }
        return 120000

    def get_investment_summary(self, user_id):
        assert user_id == 7
        return {"total_contributed": 75000}


def test_finance_query_routes_loan_emi_with_type_and_dates():
    result = execute_finance_query(
        QueryService(),
        7,
        {
            "intent": "loan_emi",
            "category": "home",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )

    assert result == 120000


def test_finance_query_returns_total_investment_contributions():
    result = execute_finance_query(
        QueryService(),
        7,
        {
            "intent": "investment",
            "category": None,
            "start_date": None,
            "end_date": None,
        },
    )

    assert result == 75000
