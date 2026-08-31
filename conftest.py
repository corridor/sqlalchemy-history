import typing as t

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_sync_database_url(database: str) -> str:  # pragma: no cover
    urls = {
        "postgres": "postgresql://postgres:postgres@localhost/sqlalchemy_history_test",
        "mysql": "mysql+pymysql://root@localhost/sqlalchemy_history_test",
        "sqlite": "sqlite:///:memory:",
        "mssql": "mssql+pyodbc://sa:MSsql2022@localhost:1433/master?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes",
        "oracle": "oracle+oracledb://SYSTEM:Oracle2022@localhost:1521/?service_name=XEPDB1",
    }
    return urls[database]


@pytest.fixture(scope="session")
def engine(pytestconfig) -> t.Iterator[Engine]:
    engine = create_engine(get_sync_database_url(pytestconfig.getvalue("db")))
    yield engine
    engine.dispose()


def pytest_addoption(parser):
    parser.addoption(
        "--db",
        choices=("sqlite", "postgres", "mysql", "mssql", "oracle"),
        default="sqlite",
        help="Database backend to use for the test suite (default: sqlite)",
    )


def pytest_collection_modifyitems(config, items):
    database = config.getvalue("db")
    for item in items:
        for marker in item.iter_markers(name="skip_db"):
            if database in marker.args:
                item.add_marker(pytest.mark.skip(reason=marker.kwargs["reason"]))
