from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)


class ModelEvaluator:

    def evaluate(self, y_true, y_pred):

        results = {
            "accuracy": accuracy_score(
                y_true,
                y_pred
            ),

            "precision": precision_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            ),

            "recall": recall_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            ),

            "f1": f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            )
        }

        return results

    def report(self, y_true, y_pred):

        print(
            classification_report(
                y_true,
                y_pred,
                zero_division=0
            )
        )

    def confusion_matrix(
        self,
        y_true,
        y_pred
    ):

        return confusion_matrix(
            y_true,
            y_pred
        )