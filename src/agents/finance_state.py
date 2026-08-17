from typing import Optional, Annotated

from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class FinanceState(TypedDict, total=False):

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    user_id: int

    intent: Optional[str]
    category: Optional[str]

    start_date: Optional[str]
    end_date: Optional[str]

    resolved_query: Optional[str]

    ai_status: Optional[str]

    finance_result: Optional[object]

    preferences: Optional[dict]
