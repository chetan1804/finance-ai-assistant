from src.tools.tool_executor import (
    FinanceToolExecutor
)


def main():

    agent = FinanceToolExecutor()

    print("\nFinance AI Tool Assistant")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("You: ")

        if question.lower() == "exit":

            break

        try:

            answer = agent.execute(
                question
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