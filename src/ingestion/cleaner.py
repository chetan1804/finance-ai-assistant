import pandas as pd


class TransactionCleaner:

    REQUIRED_COLUMNS = [
        "date",
        "description",
        "amount",
        "type",
        "merchant"
    ]

    def clean(self, df):

        df = df.copy()

        # Remove completely empty rows
        df = df.dropna(how="all")

        # Clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        # Remove spaces from text
        for column in [
            "description",
            "type",
            "merchant"
        ]:
            df[column] = (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

        # Convert date
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        # Convert amount
        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce"
        )

        # Remove invalid amounts
        df = df[df["amount"].notna()]

        # Remove invalid dates
        df = df[df["date"].notna()]

        # Normalize transaction type
        df["type"] = (
            df["type"]
            .str.lower()
            .str.strip()
        )

        # Keep only valid transaction types
        df = df[
            df["type"].isin(
                ["income", "expense", "transfer"]
            )
        ]

        # Remove duplicate rows
        df = df.drop_duplicates()

        return df.reset_index(drop=True)