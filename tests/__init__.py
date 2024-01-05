from copy import copy
import inspect
import itertools as it
import os
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, column_property, close_all_sessions, declarative_base
from sqlalchemy_history import (
    ClassNotVersioned,
    version_class,
    make_versioned,
    versioning_manager,
    remove_versioning,
)
from sqlalchemy_history.transaction import TransactionFactory
from sqlalchemy_history.plugins import TransactionMetaPlugin, TransactionChangesPlugin


class QueryPool(object):
    queries = []


@sa.event.listens_for(sa.engine.Engine, "before_cursor_execute")
def log_sql(conn, cursor, statement, parameters, context, executemany):
    QueryPool.queries.append(statement)


def get_dns_from_driver(driver):  # pragma: no cover
    if driver == "postgres":
        return "postgresql://postgres:postgres@localhost/sqlalchemy_history_test"
    elif driver == "mysql":
        return "mysql+pymysql://root@localhost/sqlalchemy_history_test"
    elif driver == "sqlite":
        return "sqlite:///:memory:"
    elif driver == "mssql":
        return "mssql+pymssql://sa:MSsql2022@localhost:1433"
    elif driver == "oracle":
        return "oracle+cx_oracle://SYSTEM:Oracle2022@localhost:1521"
    else:
        raise Exception("Unknown driver given: %r" % driver)


class TestCase(object):
    versioning_strategy = "subquery"
    transaction_column_name = "transaction_id"
    end_transaction_column_name = "end_transaction_id"
    composite_pk = False
    plugins = [TransactionChangesPlugin(), TransactionMetaPlugin()]
    transaction_cls = TransactionFactory()
    user_cls = None
    should_create_models = True

    @property
    def options(self):
        return {
            "create_models": self.should_create_models,
            "base_classes": (self.Model,),
            "strategy": self.versioning_strategy,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    @pytest.fixture
    def setup_declarative_base(self):
        self.Model = declarative_base()
        yield
        del self.Model

    @pytest.fixture
    def setup_versioning(self, setup_declarative_base):
        make_versioned(options=self.options, plugins=self.plugins)
        versioning_manager.transaction_cls = self.transaction_cls
        versioning_manager.user_cls = self.user_cls
        yield

    @pytest.fixture
    def setup_engine(self, setup_versioning):
        if "DB" not in os.environ:  # pragma: no cover
            # NOTE: We set DB environment variable explicitly if someone has not provided as this value
            #       is used to skip other test cases and if one doesn't specifiy this value tests starts
            #       breaking. We don't cover this in coverage as our CI always
            #       specifies DB variable
            os.environ["DB"] = "sqlite"
        self.driver = os.environ.get("DB")
        self.engine = create_engine(get_dns_from_driver(self.driver))
        yield
        self.engine.dispose()

    @pytest.fixture
    def setup_models(self, setup_engine):
        self.create_models()
        sa.orm.configure_mappers()
        yield

    @pytest.fixture
    def setup_connection(self, setup_models):
        self.connection = self.engine.connect()
        yield
        self.connection.close()

    @pytest.fixture
    def setup_tables(self, setup_connection):
        if hasattr(self, "Article"):
            try:
                self.ArticleVersion = version_class(self.Article)
            except ClassNotVersioned:
                pass
        if hasattr(self, "Tag"):
            try:
                self.TagVersion = version_class(self.Tag)
            except ClassNotVersioned:
                pass
        self.create_tables()
        yield
        self.drop_tables()

    @pytest.fixture(autouse=True)
    def setup_session(self, setup_tables):
        Session = sessionmaker(bind=self.connection)
        self.session = Session(autoflush=False, future=True)
        yield
        self.session.rollback()
        uow_leaks = versioning_manager.units_of_work
        session_map_leaks = versioning_manager.session_connection_map

        remove_versioning()
        QueryPool.queries = []
        versioning_manager.reset()

        close_all_sessions()
        self.session.expunge_all()

        assert not uow_leaks
        assert not session_map_leaks

    def create_tables(self):
        with self.connection.begin():
            self.Model.metadata.create_all(self.connection)

    def drop_tables(self):
        with self.connection.begin():
            self.Model.metadata.drop_all(self.connection)

    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

            # Dynamic column cotaining all text content data
            fulltext_content = column_property(name + content + description)

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = sa.orm.relationship(Article, backref="tags")

        self.Article = Article
        self.Tag = Tag


setting_variants = {
    "versioning_strategy": [
        "subquery",
        "validity",
    ],
    "transaction_column_name": ["transaction_id", "tx_id"],
    "end_transaction_column_name": ["end_transaction_id", "end_tx_id"],
}


def create_test_cases(base_class, setting_variants=setting_variants):
    """
    Function for creating bunch of test case classes for given base class
    and setting variants. Number of test cases created is the number of linear
    combinations with setting variants.

    :param base_class:
        Base test case class, should be in format 'xxxTestCase'
    :param setting_variants:
        A dictionary with keys as versioned configuration option keys and
        values as list of possible option values.
    """
    names = sorted(setting_variants)
    combinations = [
        dict(zip(names, prod)) for prod in it.product(*(setting_variants[name] for name in names))
    ]

    # Get the module where this function was called in.
    frm = inspect.stack()[1]
    module = inspect.getmodule(frm[0])

    class_suffix = base_class.__name__[0 : -len("TestCase")]  # noqa: E203
    for index, combination in enumerate(combinations):
        class_name = "Test%s%i" % (class_suffix, index)
        # Assign a new test case class for current module.
        setattr(module, class_name, type(class_name, (base_class,), combination))
