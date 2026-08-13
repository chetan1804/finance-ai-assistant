from langchain_core.messages import HumanMessage

from src.agent.graph import build_graph

# from src.database.db import close_connection


def main():

    graph = build_graph()

    print()

    print("=" * 60)

    print(
        "        FINANCE AI - LANGGRAPH AGENT"
    )

    print("=" * 60)

    print(
        "Type 'exit' to quit."
    )

    print()

    try:

        while True:

            question = input(
                "You: "
            )

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
                        ]
                    }
                )

                final_message = (
                    result["messages"][-1]
                )

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