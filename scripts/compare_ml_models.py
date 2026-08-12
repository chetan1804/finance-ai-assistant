import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.linear_model import LogisticRegression

from sklearn.naive_bayes import MultinomialNB

from sklearn.ensemble import RandomForestClassifier

from src.ml.evaluation import ModelEvaluator


def main():

    # -----------------------------------------
    # Load training data
    # -----------------------------------------

    df = pd.read_csv(
        "data/ml/large_training_data.csv"
    )

    # -----------------------------------------
    # Create text feature
    # -----------------------------------------

    df["text"] = (
        df["description"].fillna("")
        + " "
        + df["merchant"].fillna("")
    )

    X = df["text"]

    y = df["category"]

    # -----------------------------------------
    # Train/Test split
    # -----------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # -----------------------------------------
    # Models
    # -----------------------------------------

    models = {

        "Logistic Regression": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2)
                )
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=1000
                )
            )
        ]),

        "Naive Bayes": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2)
                )
            ),
            (
                "model",
                MultinomialNB()
            )
        ]),

        "Random Forest": Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2)
                )
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=42
                )
            )
        ])
    }

    evaluator = ModelEvaluator()

    results = []

    # -----------------------------------------
    # Train and evaluate
    # -----------------------------------------

    for name, model in models.items():

        print(
            f"\nTraining: {name}"
        )

        model.fit(
            X_train,
            y_train
        )

        predictions = model.predict(
            X_test
        )

        metrics = evaluator.evaluate(
            y_test,
            predictions
        )

        results.append({
            "model": name,
            **metrics
        })

        print(
            f"Accuracy : {metrics['accuracy']:.4f}"
        )

        print(
            f"Precision: {metrics['precision']:.4f}"
        )

        print(
            f"Recall   : {metrics['recall']:.4f}"
        )

        print(
            f"F1 Score : {metrics['f1']:.4f}"
        )

    # -----------------------------------------
    # Comparison
    # -----------------------------------------

    results_df = pd.DataFrame(results)

    print("\n")
    print("=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)

    print(
        results_df
        .sort_values(
            "f1",
            ascending=False
        )
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()