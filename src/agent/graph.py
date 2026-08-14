import sqlite3

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.prebuilt import (
    ToolNode,
    tools_condition,
)

from langgraph.checkpoint.sqlite import SqliteSaver

from src.agent.state import AgentState
from src.agent.nodes import (
    call_llm,
    TOOLS,
)


CHECKPOINT_DATABASE = "data/checkpoints.db"


def build_graph():

    graph = StateGraph(
        AgentState
    )

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    graph.add_node(
        "llm",
        call_llm
    )

    # --------------------------------------------------------
    # TOOLS
    # --------------------------------------------------------

    graph.add_node(
        "tools",
        ToolNode(TOOLS)
    )

    # --------------------------------------------------------
    # START -> LLM
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "llm"
    )

    # --------------------------------------------------------
    # LLM -> TOOL or END
    # --------------------------------------------------------

    graph.add_conditional_edges(
        "llm",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        }
    )

    # --------------------------------------------------------
    # TOOL -> LLM
    # --------------------------------------------------------

    graph.add_edge(
        "tools",
        "llm"
    )

    # --------------------------------------------------------
    # CHECKPOINTER
    # --------------------------------------------------------

    connection = sqlite3.connect(
        CHECKPOINT_DATABASE,
        check_same_thread=False
    )

    checkpointer = SqliteSaver(
        connection
    )

    # --------------------------------------------------------
    # COMPILE
    # --------------------------------------------------------

    return graph.compile(
        checkpointer=checkpointer
    )