import os
from operator import add
from typing import Annotated, TypedDict
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph

from src.agents.checkpoint import (
    close_checkpoint_pools,
    create_checkpointer,
    get_checkpoint_url,
)


class SharedState(TypedDict):
    values: Annotated[list[str], add]


def shared_graph(checkpointer):
    builder = StateGraph(SharedState)
    builder.add_node("finish", lambda _state: {})
    builder.add_edge(START, "finish")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


def test_checkpoint_url_follows_finance_database(monkeypatch):
    database_url = "postgresql://finance@example.test/finance"
    monkeypatch.setenv("FINANCE_DATABASE_URL", database_url)
    monkeypatch.delenv("FINANCE_CHECKPOINT_URL", raising=False)
    monkeypatch.delenv("FINANCE_CHECKPOINT_PATH", raising=False)

    assert get_checkpoint_url() == database_url


def test_explicit_sqlite_checkpoint_path_overrides_finance_database(monkeypatch):
    monkeypatch.setenv("FINANCE_DATABASE_URL", "postgresql://finance@example.test/finance")
    monkeypatch.setenv("FINANCE_CHECKPOINT_PATH", "/tmp/checkpoints.db")
    monkeypatch.delenv("FINANCE_CHECKPOINT_URL", raising=False)

    assert get_checkpoint_url() is None


def test_checkpoint_url_and_path_cannot_both_be_configured(monkeypatch):
    monkeypatch.setenv("FINANCE_CHECKPOINT_URL", "postgresql://finance@example.test/finance")
    monkeypatch.setenv("FINANCE_CHECKPOINT_PATH", "/tmp/checkpoints.db")

    with pytest.raises(RuntimeError, match="Configure only one"):
        get_checkpoint_url()


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="TEST_POSTGRES_URL is required for PostgreSQL integration testing.",
)
def test_postgres_checkpoints_persist_between_savers(monkeypatch):
    monkeypatch.setenv("FINANCE_CHECKPOINT_URL", os.environ["TEST_POSTGRES_URL"])
    monkeypatch.delenv("FINANCE_CHECKPOINT_PATH", raising=False)
    config = {"configurable": {"thread_id": f"checkpoint-{uuid4().hex}"}}

    first = create_checkpointer()
    assert isinstance(first, PostgresSaver)
    shared_graph(first).invoke({"values": ["first"]}, config=config)

    second = create_checkpointer()
    result = shared_graph(second).invoke({"values": ["second"]}, config=config)
    close_checkpoint_pools()

    assert result["values"] == ["first", "second"]
