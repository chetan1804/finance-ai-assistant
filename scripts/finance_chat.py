from src.qa.query_parser import FinancialQueryParser
from src.qa.finance_qa import FinanceQA
from src.qa.response_generator import (
    FinancialResponseGenerator
)


def main():

    parser = FinancialQueryParser()

    qa = FinanceQA()

    response_generator = (
        FinancialResponseGenerator()
    )

    print("\nFinance AI Assistant")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("You: ")

        if question.lower() == "exit":
            break

        try:

            query = parser.parse(
                question
            )

            result = qa.execute(
                query
            )

            answer = (
                response_generator
                .generate(
                    question,
                    result
                )
            )

            print(
                f"\nAssistant: {answer}\n"
            )

        except Exception as error:

            print(
                f"\nError: {error}\n"
            )


if __name__ == "__main__":
    main()