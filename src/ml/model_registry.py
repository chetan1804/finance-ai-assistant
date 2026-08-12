from pathlib import Path
import joblib


class ModelRegistry:

    def __init__(self, model_directory="data/ml/models"):

        self.model_directory = Path(
            model_directory
        )

        self.model_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    def save(self, model, name):

        path = (
            self.model_directory
            / f"{name}.joblib"
        )

        joblib.dump(
            model,
            path
        )

        return path

    def load(self, name):

        path = (
            self.model_directory
            / f"{name}.joblib"
        )

        return joblib.load(path)