class TransactionValidator:

    REQUIRED_COLUMNS = [
        "date",
        "description",
        "amount",
        "type",
        "merchant"
    ]

    VALID_TYPES = [
        "income",
        "expense",
        "transfer"
    ]

    def validate(self, df):

        errors = []

        # Check required columns
        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:

            errors.append(
                f"Missing columns: {missing_columns}"
            )

        if "amount" in df.columns:

            if (df["amount"] <= 0).any():

                errors.append(
                    "Amount must be greater than zero."
                )

        if "type" in df.columns:

            invalid_types = set(
                df["type"]
            ) - set(self.VALID_TYPES)

            if invalid_types:

                errors.append(
                    f"Invalid transaction types: "
                    f"{invalid_types}"
                )

        return errors