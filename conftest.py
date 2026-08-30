import pytest


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
