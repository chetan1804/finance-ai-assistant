from src.qa.query_parser import FinancialQueryParser
from src.qa.finance_qa import FinanceQA


def main():

    parser = FinancialQueryParser()

    qa = FinanceQA()

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

        print("\n")
        print("=" * 60)

        print("QUESTION:")
        print(question)

        query = parser.parse(
            question
        )

        print("\nINTENT:")
        print(query.model_dump())

        result = qa.execute(
            query
        )

        print("\nRESULT:")
        print(result)


if __name__ == "__main__":
    main()