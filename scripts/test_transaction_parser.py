from src.llm.transaction_parser import TransactionParser


def main():

    parser = TransactionParser()

    examples = [

        "I spent ₹850 on dinner at a restaurant yesterday.",

        "I received my salary of ₹80,000 today.",

        "I paid ₹2,500 for fuel.",

        "I bought groceries for ₹3,200 from DMart."
    ]

    for text in examples:

        print("\n")
        print("=" * 60)
        print("INPUT:")
        print(text)

        result = parser.parse(text)

        print("\nSTRUCTURED OUTPUT:")
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()