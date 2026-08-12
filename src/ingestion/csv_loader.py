import pandas as pd


class CSVLoader:

    def load(self, file_path):

        df = pd.read_csv(file_path)

        return df