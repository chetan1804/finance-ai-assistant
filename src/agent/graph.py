from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.prebuilt import (
    ToolNode,
    tools_condition,
)

from src.agent.state import AgentState

from src.agent.nodes import (
    call_llm,
    TOOLS,
)


def build_graph():

    # --------------------------------------------------------
    # Create graph
    # --------------------------------------------------------

    graph = StateGraph(
        AgentState
    )

    # --------------------------------------------------------
    # Add LLM node
    # --------------------------------------------------------

    graph.add_node(
        "llm",
        call_llm
    )

    # --------------------------------------------------------
    # Add ToolNode
    # --------------------------------------------------------

    graph.add_node(
        "tools",
        ToolNode(TOOLS)
    )

    # --------------------------------------------------------
    # START → LLM
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "llm"
    )

    # --------------------------------------------------------
    # LLM → TOOLS or END
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
    # TOOLS → LLM
    # --------------------------------------------------------

    graph.add_edge(
        "tools",
        "llm"
    )

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    return graph.compile()