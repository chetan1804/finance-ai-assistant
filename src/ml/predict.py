from src.ml.train_classifier import TransactionClassifier


class TransactionPredictor:

    def __init__(self, model_path):

        self.classifier = TransactionClassifier()

        self.classifier.load(
            model_path
        )

    def predict(
        self,
        description,
        merchant=""
    ):

        text = (
            f"{description} {merchant}"
        )

        prediction = self.classifier.predict(
            [text]
        )

        return prediction[0]