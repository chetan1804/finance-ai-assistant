import atexit
import os
import sqlite3
import threading
from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from src.database.db import get_data_directory, get_database_url


_CHECKPOINT_POOLS = {}
_CHECKPOINT_POOLS_LOCK = threading.Lock()


def get_checkpoint_database():
    configured = os.getenv("FINANCE_CHECKPOINT_PATH")
    return (
        Path(configured).expanduser()
        if configured
        else get_data_directory() / "checkpoints.db"
    )


def get_checkpoint_url():
    configured = os.getenv("FINANCE_CHECKPOINT_URL")
    if configured and os.getenv("FINANCE_CHECKPOINT_PATH"):
        raise RuntimeError(
            "Configure only one of FINANCE_CHECKPOINT_URL or "
            "FINANCE_CHECKPOINT_PATH."
        )
    if configured and not configured.startswith(("postgresql://", "postgres://")):
        raise RuntimeError("FINANCE_CHECKPOINT_URL must use PostgreSQL.")
    if configured:
        return configured
    if os.getenv("FINANCE_CHECKPOINT_PATH"):
        return None
    return get_database_url()


def _checkpoint_pool_size(name, default):
    value = os.getenv(name)
    try:
        parsed = int(value) if value is not None else default
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer.") from error
    if parsed < 1:
        raise RuntimeError(f"{name} must be at least 1.")
    return parsed


def get_checkpoint_pool(checkpoint_url=None):
    checkpoint_url = checkpoint_url or get_checkpoint_url()
    if not checkpoint_url:
        return None
    min_size = _checkpoint_pool_size("FINANCE_CHECKPOINT_POOL_MIN_SIZE", 1)
    max_size = _checkpoint_pool_size("FINANCE_CHECKPOINT_POOL_MAX_SIZE", 5)
    if min_size > max_size:
        raise RuntimeError(
            "FINANCE_CHECKPOINT_POOL_MIN_SIZE must not exceed "
            "FINANCE_CHECKPOINT_POOL_MAX_SIZE."
        )
    key = (checkpoint_url, min_size, max_size)
    with _CHECKPOINT_POOLS_LOCK:
        pool = _CHECKPOINT_POOLS.get(key)
        if pool is None:
            pool = ConnectionPool(
                checkpoint_url,
                min_size=min_size,
                max_size=max_size,
                timeout=5,
                check=ConnectionPool.check_connection,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
                open=True,
                name="finance-checkpoints",
            )
            _CHECKPOINT_POOLS[key] = pool
    return pool


def close_checkpoint_pools():
    with _CHECKPOINT_POOLS_LOCK:
        pools = list(_CHECKPOINT_POOLS.values())
        _CHECKPOINT_POOLS.clear()
    for pool in pools:
        pool.close()


atexit.register(close_checkpoint_pools)


def create_checkpointer():
    checkpoint_url = get_checkpoint_url()
    serializer = JsonPlusSerializer(allowed_msgpack_modules=None)
    if checkpoint_url:
        checkpointer = PostgresSaver(
            get_checkpoint_pool(checkpoint_url),
            serde=serializer,
        )
    else:
        checkpoint_database = get_checkpoint_database()
        checkpoint_database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            checkpoint_database,
            check_same_thread=False,
        )
        checkpointer = SqliteSaver(conn=connection, serde=serializer)
    checkpointer.setup()
    return checkpointer


def checkpoint_storage_is_ready():
    checkpoint_url = get_checkpoint_url()
    if checkpoint_url:
        with get_checkpoint_pool(checkpoint_url).connection() as connection:
            return connection.execute("SELECT 1 AS ready").fetchone()["ready"] == 1
    checkpoint_database = get_checkpoint_database()
    checkpoint_database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(checkpoint_database) as connection:
        return connection.execute("SELECT 1").fetchone()[0] == 1
