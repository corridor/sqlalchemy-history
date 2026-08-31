import typing as t

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def get_async_database_url(database: str) -> str:  # pragma: no cover
    urls = {
        "postgres": "postgresql+asyncpg://postgres:postgres@localhost/sqlalchemy_history_test",
        "mysql": "mysql+aiomysql://root@localhost/sqlalchemy_history_test",
        "sqlite": "sqlite+aiosqlite:///:memory:",
        "mssql": "mssql+aioodbc://sa:MSsql2022@localhost:1433/master?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
        "oracle": "oracle+oracledb://SYSTEM:Oracle2022@localhost:1521/?service_name=XEPDB1",
    }
    return urls[database]


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def async_engine(anyio_backend, pytestconfig) -> t.AsyncIterator[AsyncEngine]:
    engine = create_async_engine(get_async_database_url(pytestconfig.getvalue("db")))
    yield engine
    await engine.dispose()
