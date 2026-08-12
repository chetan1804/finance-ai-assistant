from src.ingestion.csv_loader import CSVLoader
from src.ingestion.cleaner import TransactionCleaner
from src.ingestion.validator import TransactionValidator


class TransactionPipeline:

    def __init__(self):

        self.loader = CSVLoader()
        self.cleaner = TransactionCleaner()
        self.validator = TransactionValidator()

    def process(self, file_path):

        # 1. Load
        df = self.loader.load(file_path)

        print(f"Loaded {len(df)} rows")

        # 2. Clean
        df = self.cleaner.clean(df)

        print(f"After cleaning: {len(df)} rows")

        # 3. Validate
        errors = self.validator.validate(df)

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        print("Validation successful")

        return df