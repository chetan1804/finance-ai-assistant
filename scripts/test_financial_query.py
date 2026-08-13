from src.qa.query_parser import FinancialQueryParser


def main():

    parser = FinancialQueryParser()

    questions = [
        "How much did I earn?",
        "How much did I spend?",
        "How much did I save?",
        "How much did I spend on food?",
        "What was my biggest expense?",
        "How much did I spend on Amazon?",
        "How many transactions do I have?"
    ]

    for question in questions:

        result = parser.parse(question)

        print("\nQuestion:")
        print(question)

        print("\nParsed:")
        print(
            result.model_dump_json(
                indent=2
            )
        )


if __name__ == "__main__":
    main()