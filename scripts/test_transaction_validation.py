from src.llm.transaction_parser import TransactionParser
from src.services.transaction_validator import (
    TransactionValidator
)


def main():

    parser = TransactionParser()

    validator = TransactionValidator()

    text = (
        "I spent ₹850 on dinner "
        "at a restaurant yesterday."
    )

    transaction = parser.parse(text)

    print("Extracted:")
    print(
        transaction.model_dump_json(
            indent=2
        )
    )

    validator.validate(
        transaction
    )

    print("\nValidation successful!")


if __name__ == "__main__":
    main()