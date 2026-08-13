from src.llm.llm_client import get_llm


def main():

    llm = get_llm()

    response = llm.invoke(
        "Explain financial planning in one sentence."
    )

    print("\nLLM Response:")
    print(response.content)


if __name__ == "__main__":
    main()