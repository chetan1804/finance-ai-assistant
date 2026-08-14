import argparse

from src.agents.finance_agent import chat


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the personalized finance assistant."
    )
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--thread-id", default="finance-chat")
    return parser.parse_args()


def main():

    args = parse_args()

    print("\nFinance AI Assistant - Step 15")
    print("Type 'exit' to quit.\n")

    while True:

        question = input("You: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        try:

            result = chat(
                user_id=args.user_id,
                thread_id=args.thread_id,
                question=question,
            )

            messages = result.get("messages", [])

            if messages:

                print(
                    "\nAssistant:",
                    messages[-1].content
                )

            print()

        except Exception as e:

            print(
                f"\nError: {e}\n"
            )


if __name__ == "__main__":
    main()
