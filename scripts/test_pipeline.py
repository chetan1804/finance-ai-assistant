from src.ingestion.pipeline import TransactionPipeline


def main():

    pipeline = TransactionPipeline()

    df = pipeline.process(
        "data/raw/sample_transactions.csv"
    )

    print("\nProcessed Data:")
    print(df)

    print("\nSummary:")
    print(df.groupby("type")["amount"].sum())


if __name__ == "__main__":
    main()