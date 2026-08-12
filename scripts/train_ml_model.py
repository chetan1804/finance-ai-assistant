import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from src.ml.train_classifier import TransactionClassifier


def main():

    # Load dataset
    df = pd.read_csv(
        "data/ml/training_data.csv"
    )

    # Combine description and merchant
    df["text"] = (
        df["description"].fillna("")
        + " "
        + df["merchant"].fillna("")
    )

    X = df["text"]

    y = df["category"]

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # Create model
    classifier = TransactionClassifier()

    # Train
    classifier.train(
        X_train,
        y_train
    )

    # Predict
    predictions = classifier.predict(
        X_test
    )

    # Evaluation
    print("\nClassification Report")
    print("---------------------")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0
        )
    )

    # Save
    classifier.save(
        "data/ml/transaction_classifier.joblib"
    )

    print(
        "\nModel saved successfully."
    )


if __name__ == "__main__":
    main()