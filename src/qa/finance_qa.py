from src.services.finance_service import FinanceService


class FinanceQA:

    def __init__(self):

        self.finance_service = (
            FinanceService()
        )

    def execute(self, query):

        intent = query.intent

        if intent == "total_income":

            return {
                "result": self.finance_service.total_income()
            }

        if intent == "total_expenses":

            return {
                "result": self.finance_service.total_expenses()
            }

        if intent == "total_savings":

            return {
                "result": self.finance_service.total_savings()
            }

        if intent == "category_expenses":

            if not query.category:

                raise ValueError(
                    "Category is required."
                )

            return {
                "category": query.category,
                "result": (
                    self.finance_service
                    .category_expenses(
                        query.category
                    )
                )
            }

        if intent == "largest_expense":

            expense = (
                self.finance_service
                .largest_expense()
            )

            return {
                "result": expense
            }

        if intent == "merchant_expenses":

            if not query.merchant:

                raise ValueError(
                    "Merchant is required."
                )

            return {
                "merchant": query.merchant,
                "result": (
                    self.finance_service
                    .merchant_expenses(
                        query.merchant
                    )
                )
            }

        if intent == "transaction_count":

            return {
                "result": (
                    self.finance_service
                    .transaction_count()
                )
            }

        raise ValueError(
            f"Unsupported intent: {intent}"
        )