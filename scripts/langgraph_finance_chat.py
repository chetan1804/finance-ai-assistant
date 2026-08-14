from langchain_core.messages import HumanMessage

from src.agent.graph import build_graph

def main():

    graph = build_graph()

    thread_id = "user-1-session-1"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

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

                result = graph.invoke(
                    {
                        "messages": [
                            HumanMessage(
                                content=question
                            )
                        ],
                        "user_id": 1
                    },
                    config=config
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