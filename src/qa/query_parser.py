from langchain_core.prompts import ChatPromptTemplate

from src.llm.llm_client import get_llm
from src.qa.prompts import SYSTEM_PROMPT
from src.qa.schemas import FinancialQuery


class FinancialQueryParser:

    def __init__(self):

        self.llm = get_llm()

        self.structured_llm = (
            self.llm.with_structured_output(
                FinancialQuery
            )
        )

        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                SYSTEM_PROMPT
            ),
            (
                "human",
                "{question}"
            )
        ])

        self.chain = (
            self.prompt
            | self.structured_llm
        )

    def parse(self, question):

        return self.chain.invoke({
            "question": question
        })