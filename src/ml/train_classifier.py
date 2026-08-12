import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


class TransactionClassifier:

    def __init__(self):

        self.model = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
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

    def train(self, texts, labels):

        self.model.fit(
            texts,
            labels
        )

    def predict(self, texts):

        return self.model.predict(texts)

    def save(self, path):

        joblib.dump(
            self.model,
            path
        )

    def load(self, path):

        self.model = joblib.load(
            path
        )