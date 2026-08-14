import sqlite3
from datetime import date
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from src.agents.context import parse_context
from src.agents.finance_state import FinanceState
from src.agents.personalization import format_money
from src.database.finance_service import FinanceService
from src.llm.llm_client import get_llm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DATABASE = PROJECT_ROOT / "data" / "checkpoints.db"

llm = get_llm()
finance_service = FinanceService()


def extract_context(state: FinanceState):
    """Resolve the latest request using the user's remembered conversation."""
    user_messages = [
        f"USER: {message.content}"
        for message in state.get("messages", [])
        if isinstance(message, HumanMessage)
    ]

    if not user_messages:
        return parse_context("")

    prompt = f"""
Analyze the current personal-finance request using its conversation history.
Today's date is {date.today().isoformat()}.

Conversation:
{chr(10).join(user_messages)}

Return only these five lines:
INTENT: <expense|income|category_expense|balance|unknown>
CATEGORY: <category or NONE>
START_DATE: <YYYY-MM-DD or NONE>
END_DATE: <YYYY-MM-DD or NONE>
RESOLVED_QUERY: <the current request as a standalone question>

Rules:
- "How much did I spend?" is expense.
- "How much did I spend on food?" is category_expense with category food.
- Balance and savings questions use balance.
- Resolve follow-ups from earlier user messages in this conversation.
- Convert relative dates such as this month or last month using today's date.
- Do not invent a date when the user did not specify a period.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You extract structured finance intent and context."
            ),
            HumanMessage(content=prompt),
        ]
    )
    return parse_context(response.content)


def finance_query(state: FinanceState):
    """Execute a user-scoped database query selected from validated context."""
    user_id = state["user_id"]
    intent = state.get("intent")
    category = state.get("category")
    start_date = state.get("start_date")
    end_date = state.get("end_date")

    common = {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    if intent == "category_expense" and category:
        result = finance_service.get_category_expenses(
            category=category,
            **common,
        )
    elif intent == "expense":
        result = finance_service.get_total_expenses(**common)
    elif intent == "income":
        result = finance_service.get_total_income(**common)
    elif intent == "balance":
        result = finance_service.get_savings(**common)
    else:
        result = None

    return {
        "finance_result": result,
        "preferences": finance_service.get_user_preferences(user_id),
    }


def generate_response(state: FinanceState):
    """Generate a short response using only the verified database result."""
    user_question = next(
        (
            message.content
            for message in reversed(state.get("messages", []))
            if isinstance(message, HumanMessage)
        ),
        "",
    )
    result = state.get("finance_result")
    preferences = state.get("preferences") or {}
    language = preferences.get("language", "English")
    currency = preferences.get("currency", "INR")

    if result is None:
        prompt = (
            f"Politely ask the user to clarify this finance request: "
            f"{user_question}"
        )
    else:
        formatted_result = format_money(result, currency)
        prompt = f"""
User question: {user_question}
Resolved question: {state.get('resolved_query') or user_question}
Intent: {state.get('intent')}
Category: {state.get('category') or 'none'}
Database result: {result}
Display amount: {formatted_result}
Preferred language: {language}
Preferred currency: {currency}

Answer directly and briefly in the preferred language.
Use only the database result and never invent a number.
Use the display amount exactly as provided; do not reformat it.
If the result is 0, state that clearly.
"""

    response = llm.invoke(
        [
            SystemMessage(
                content="You are an accurate personal finance assistant."
            ),
            HumanMessage(content=prompt),
        ]
    )
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(FinanceState)
    graph.add_node("extract_context", extract_context)
    graph.add_node("finance_query", finance_query)
    graph.add_node("generate_response", generate_response)
    graph.add_edge(START, "extract_context")
    graph.add_edge("extract_context", "finance_query")
    graph.add_edge("finance_query", "generate_response")
    graph.add_edge("generate_response", END)
    return graph


checkpoint_connection = sqlite3.connect(
    CHECKPOINT_DATABASE,
    check_same_thread=False,
)


def create_app():
    checkpointer = SqliteSaver(conn=checkpoint_connection)
    checkpointer.setup()
    return build_graph().compile(checkpointer=checkpointer)


app = create_app()


def chat(user_id: int, thread_id: str, question: str):
    """Run one personalized turn, isolated by both user and thread."""
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer.")
    if not thread_id.strip():
        raise ValueError("thread_id is required.")
    if not question.strip():
        raise ValueError("question is required.")

    config = {
        "configurable": {
            "thread_id": f"user-{user_id}:{thread_id.strip()}"
        }
    }
    state: FinanceState = {
        "messages": [HumanMessage(content=question.strip())],
        "user_id": user_id,
    }
    return app.invoke(state, config=config)
