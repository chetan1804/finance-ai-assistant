import pandas as pd


class FinanceAnalyzer:

    def __init__(self, dataframe):
        self.df = dataframe.copy()

    def summary(self):

        income = self.df.loc[
            self.df["type"] == "income",
            "amount"
        ].sum()

        expenses = self.df.loc[
            self.df["type"] == "expense",
            "amount"
        ].sum()

        savings = income - expenses

        savings_rate = (
            (savings / income) * 100
            if income > 0
            else 0
        )

        return {
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "savings_rate": savings_rate
        }

    def expenses_by_category(self):

        expenses = self.df[
            self.df["type"] == "expense"
        ]

        return (
            expenses
            .groupby("category")["amount"]
            .sum()
            .sort_values(ascending=False)
        )

    def expenses_by_merchant(self):

        expenses = self.df[
            self.df["type"] == "expense"
        ]

        return (
            expenses
            .groupby("merchant")["amount"]
            .sum()
            .sort_values(ascending=False)
        )

    def monthly_summary(self):

        df = self.df.copy()

        df["date"] = pd.to_datetime(df["date"])

        df["month"] = (
            df["date"]
            .dt.to_period("M")
        )

        income = (
            df[df["type"] == "income"]
            .groupby("month")["amount"]
            .sum()
        )

        expenses = (
            df[df["type"] == "expense"]
            .groupby("month")["amount"]
            .sum()
        )

        result = pd.DataFrame({
            "income": income,
            "expenses": expenses
        }).fillna(0)

        result["savings"] = (
            result["income"]
            - result["expenses"]
        )

        return result