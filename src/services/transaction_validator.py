from src.llm.schemas import TransactionExtraction


class TransactionValidator:

    VALID_CATEGORIES = {
        "Food",
        "Transport",
        "Shopping",
        "Bills",
        "Entertainment",
        "Salary",
        "Healthcare",
        "Education",
        "Investment",
        "Other"
    }

    def validate(
        self,
        transaction: TransactionExtraction
    ):

        errors = []

        if transaction.amount <= 0:

            errors.append(
                "Amount must be greater than zero."
            )

        if transaction.category not in self.VALID_CATEGORIES:

            errors.append(
                f"Invalid category: "
                f"{transaction.category}"
            )

        if not transaction.merchant.strip():

            errors.append(
                "Merchant cannot be empty."
            )

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        return True