"""Postgres connection pool. Every request borrows a connection and returns it."""
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

# prepare_threshold=None keeps us compatible with Supabase's connection pooler
pool = ConnectionPool(
    settings.database_url,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row, "prepare_threshold": None},
)


@contextmanager
def conn():
    """Commits automatically at the end of the block, rolls back on error."""
    with pool.connection() as c:
        yield c
