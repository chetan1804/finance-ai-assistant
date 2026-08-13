from langchain_core.prompts import ChatPromptTemplate

from src.llm.llm_client import get_llm


class FinancialResponseGenerator:

    def __init__(self):

        self.llm = get_llm()

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
You are a helpful personal finance assistant.

Answer the user's financial question using
ONLY the provided database result.

Do not invent financial information.

Keep the answer concise and easy to understand.

Use Indian Rupee formatting when appropriate.
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