import pandas as pd


class FeatureEngineer:

    def transform(self, df):

        df = df.copy()

        # Convert date
        df["date"] = pd.to_datetime(df["date"])

        # Date-based features
        df["day"] = df["date"].dt.day

        df["day_of_week"] = (
            df["date"].dt.dayofweek
        )

        df["month"] = (
            df["date"].dt.month
        )

        # Text features
        df["text"] = (
            df["description"].fillna("")
            + " "
            + df["merchant"].fillna("")
        )

        return df