import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay


def main():

    df = pd.read_csv(
        "data/ml/training_data.csv"
    )

    df["text"] = (
        df["description"].fillna("")
        + " "
        + df["merchant"].fillna("")
    )

    X = df["text"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2)
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000
            )
        )
    ])

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    ConfusionMatrixDisplay.from_predictions(
        y_test,
        predictions,
        xticks_rotation=45
    )

    plt.title(
        "Transaction Category Confusion Matrix"
    )

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()