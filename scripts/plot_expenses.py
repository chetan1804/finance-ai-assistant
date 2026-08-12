import matplotlib.pyplot as plt

from src.ingestion.pipeline import TransactionPipeline
from src.analytics.data_preparation import add_categories
from src.analytics.finance_analysis import FinanceAnalyzer


def main():

    pipeline = TransactionPipeline()

    df = pipeline.process(
        "data/raw/finance_sample.csv"
    )

    df = add_categories(df)

    analyzer = FinanceAnalyzer(df)

    category_data = (
        analyzer
        .expenses_by_category()
    )

    category_data.plot(
        kind="bar",
        figsize=(10, 6)
    )

    plt.title("Expenses by Category")
    plt.xlabel("Category")
    plt.ylabel("Amount (₹)")

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()