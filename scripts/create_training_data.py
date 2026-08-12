import pandas as pd

from src.ingestion.pipeline import TransactionPipeline
from src.services.category_service import CategoryService


def main():

    pipeline = TransactionPipeline()

    df = pipeline.process(
        "data/raw/finance_sample.csv"
    )

    category_service = CategoryService()

    df["category"] = df.apply(
        lambda row: category_service.categorize(
            row["description"],
            row["merchant"]
        ),
        axis=1
    )

    training_data = df[
        [
            "description",
            "merchant",
            "category"
        ]
    ]

    training_data.to_csv(
        "data/ml/training_data.csv",
        index=False
    )

    print(
        f"Created {len(training_data)} training records."
    )


if __name__ == "__main__":
    main()