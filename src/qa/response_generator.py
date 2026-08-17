from langchain_core.prompts import ChatPromptTemplate

from src.llm.llm_client import get_llm


class FinancialResponseGenerator:

    def __init__(self):

        self.llm = get_llm()

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
                You are ArthNivo, a helpful personal finance assistant
                for users in India.

                Answer the user's financial question using
                ONLY the provided database result.

                Important:
                - All financial amounts are in Indian Rupees (INR).
                - Use ₹ for monetary values.
                - Use Indian number formatting.
                - Example: 8000 should be written as ₹8,000.
                - Example: 125000 should be written as ₹1,25,000.
                - Never convert INR to USD.
                - Never invent financial information.

                Keep the answer concise and easy to understand.
                """
            ),
            (
                "human",
                """
User question:
{question}

Database result:
{result}

Provide a concise natural-language answer.
"""
            )
        ])

        self.chain = (
            self.prompt
            | self.llm
        )

    def generate(
        self,
        question,
        result
    ):

        response = self.chain.invoke({
            "question": question,
            "result": str(result)
        })

        return response.content
