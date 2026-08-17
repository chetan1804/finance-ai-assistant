from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from src.llm.llm_client import get_llm

from src.tools.finance_tools import (
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
)


TOOLS = [
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
]


TOOL_MAP = {
    tool.name: tool
    for tool in TOOLS
}


class FinanceToolExecutor:

    def __init__(self):

        self.llm = get_llm().bind_tools(
            TOOLS
        )

    def execute(self, question):

        messages = [
            SystemMessage(
                content="""
            You are ArthNivo, a personal finance assistant for users in India.

            Use the available tools to answer financial questions.

            IMPORTANT:
            - All monetary values are in Indian Rupees (INR).
            - Format monetary values using ₹.
            - Use Indian number formatting when appropriate.
            - For example:
            8000 -> ₹8,000
            25000 -> ₹25,000
            125000 -> ₹1,25,000
            - Never use $ unless the transaction is explicitly in USD.
            - Never invent financial numbers.
            - Always use the tool result for financial calculations.
            """
            ),
            HumanMessage(
                content=question
            ),
        ]

        # -----------------------------------
        # First LLM call
        # -----------------------------------

        response = self.llm.invoke(
            messages
        )

        # Add AI response to conversation
        messages.append(response)

        # -----------------------------------
        # No tool required
        # -----------------------------------

        if not response.tool_calls:

            return response.content

        # -----------------------------------
        # Execute tools
        # -----------------------------------

        for tool_call in response.tool_calls:

            tool_name = tool_call["name"]

            tool_args = tool_call["args"]

            tool_call_id = tool_call["id"]

            tool = TOOL_MAP.get(
                tool_name
            )

            if tool is None:

                raise ValueError(
                    f"Unknown tool: {tool_name}"
                )

            print(
                f"\n[Tool] {tool_name}"
            )

            print(
                f"[Args] {tool_args}"
            )

            # Execute Python function
            tool_result = tool.invoke(
                tool_args
            )

            print(
                f"[Result] {tool_result}"
            )

            # -----------------------------------
            # IMPORTANT:
            # Preserve tool_call_id
            # -----------------------------------

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )

        # -----------------------------------
        # Second LLM call
        # -----------------------------------

        final_response = self.llm.invoke(
            messages
        )

        return final_response.content
