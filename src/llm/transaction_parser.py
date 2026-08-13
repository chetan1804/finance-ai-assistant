from datetime import date

from langchain_core.prompts import ChatPromptTemplate

from src.llm.llm_client import get_llm
from src.llm.prompts import SYSTEM_PROMPT
from src.llm.schemas import TransactionExtraction


class TransactionParser:

    def __init__(self):

        self.llm = get_llm()

        self.structured_llm = (
            self.llm.with_structured_output(
                TransactionExtraction
            )
        )

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                SYSTEM_PROMPT
            ),
            (
                "human",
                """
Today's date is {current_date}.

Extract the financial transaction
from the following user statement:

{user_input}
"""
            )
        ])

        self.chain = (
            self.prompt
            | self.structured_llm
        )

    def parse(self, user_input):

        result = self.chain.invoke({
            "current_date": date.today().isoformat(),
            "user_input": user_input
        })

        return result