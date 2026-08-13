from src.tools.tool_agent import (
    get_tool_enabled_llm
)


def main():

    llm = get_tool_enabled_llm()

    questions = [
        "How much did I spend?",
        "How much did I earn?",
        "How much did I save?",
        "How much did I spend on food?",
        "What was my biggest expense?",
        "How much did I spend on Amazon?",
        "How many transactions do I have?"
    ]

    for question in questions:

        print("\n")
        print("=" * 60)

        print("Question:")
        print(question)

        response = llm.invoke(
            question
        )

        print("\nResponse:")
        print(response)

        print("\nTool calls:")

        for tool_call in response.tool_calls:

            print(tool_call)


if __name__ == "__main__":
    main()