from src.ingestion.pipeline import TransactionPipeline
from src.analytics.data_preparation import add_categories
from src.analytics.finance_analysis import FinanceAnalyzer


def main():

    # ---------------------------------------
    # Load and clean data
    # ---------------------------------------

    pipeline = TransactionPipeline()

    df = pipeline.process(
        "data/raw/finance_sample.csv"
    )

    # ---------------------------------------
    # Add categories
    # ---------------------------------------

    df = add_categories(df)

    print("\nCategorized Transactions")
    print("------------------------")

    print(
        df[
            [
                "date",
                "description",
                "amount",
                "type",
                "merchant",
                "category"
            ]
        ].to_string(index=False)
    )

    # ---------------------------------------
    # Analyze
    # ---------------------------------------

    analyzer = FinanceAnalyzer(df)

    # ---------------------------------------
    # Financial summary
    # ---------------------------------------

    summary = analyzer.summary()

    print("\n")
    print("=" * 40)
    print("FINANCIAL SUMMARY")
    print("=" * 40)

    print(f"Income       : ₹{summary['income']:,.2f}")
    print(f"Expenses     : ₹{summary['expenses']:,.2f}")
    print(f"Savings      : ₹{summary['savings']:,.2f}")
    print(f"Savings Rate : {summary['savings_rate']:.2f}%")

    # ---------------------------------------
    # Category analysis
    # ---------------------------------------

    print("\n")
    print("=" * 40)
    print("EXPENSES BY CATEGORY")
    print("=" * 40)

    print(
        analyzer
        .expenses_by_category()
        .to_string()
    )

    # ---------------------------------------
    # Merchant analysis
    # ---------------------------------------

    print("\n")
    print("=" * 40)
    print("EXPENSES BY MERCHANT")
    print("=" * 40)

    print(
        analyzer
        .expenses_by_merchant()
        .to_string()
    )

    # ---------------------------------------
    # Monthly analysis
    # ---------------------------------------

    print("\n")
    print("=" * 40)
    print("MONTHLY SUMMARY")
    print("=" * 40)

    print(
        analyzer
        .monthly_summary()
        .to_string()
    )


if __name__ == "__main__":
    main()