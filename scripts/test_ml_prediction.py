from src.ml.predict import TransactionPredictor


def main():

    predictor = TransactionPredictor(
        "data/ml/transaction_classifier.joblib"
    )

    test_transactions = [

        (
            "Dinner at restaurant",
            "Restaurant"
        ),

        (
            "Cab ride",
            "Uber"
        ),

        (
            "Online purchase",
            "Amazon"
        ),

        (
            "Monthly electricity payment",
            "MSEDCL"
        ),

        (
            "Food delivery",
            "Swiggy"
        )
    ]

    for description, merchant in test_transactions:

        category = predictor.predict(
            description,
            merchant
        )

        print(
            f"{description:35} "
            f"-> {category}"
        )


if __name__ == "__main__":
    main()