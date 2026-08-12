from src.ingestion.csv_loader import CSVLoader


def main():

    loader = CSVLoader()

    df = loader.load(
        "data/raw/sample_transactions.csv"
    )

    print("\nLoaded Data:")
    print(df)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nShape:")
    print(df.shape)


if __name__ == "__main__":
    main()