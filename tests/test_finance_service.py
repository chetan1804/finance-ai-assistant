from src.services.finance_service import FinanceService


def test_finance_service_exists():

    service = FinanceService()

    assert service is not None