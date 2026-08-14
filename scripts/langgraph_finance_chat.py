from src.agents.finance_agent import chat

def main():

    user_id = 1
    thread_id = "user-1-session-1"

    print()
    print("=" * 60)
    print("       FINANCE AI - LANGGRAPH MEMORY")
    print("=" * 60)
    print("Type 'exit' to quit.")
    print()

    try:

        while True:

            question = input("You: ")

            if question.lower() == "exit":
                break

            if not question.strip():
                continue

            try:

                result = chat(
                    user_id=user_id,
                    thread_id=thread_id,
                    question=question,
                )

                final_message = result[
                    "messages"
                ][-1]

                print(
                    f"\nAssistant: "
                    f"{final_message.content}\n"
                )

            except Exception as error:

                print(
                    f"\nError: {error}\n"
                )

    finally:

        ""


if __name__ == "__main__":
    main()
