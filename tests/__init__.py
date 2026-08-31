import contextlib
import inspect
import itertools as it
import typing as t
from copy import copy

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    close_all_sessions,
    column_property,
    configure_mappers,
    relationship,
    sessionmaker,
)

from sqlalchemy_history import (
    ClassNotVersioned,
    make_versioned,
    remove_versioning,
    version_class,
    versioning_manager,
)
from sqlalchemy_history.plugins import TransactionChangesPlugin, TransactionMetaPlugin
from sqlalchemy_history.transaction import TransactionFactory


class QueryPool:
    queries = []


@sa.event.listens_for(sa.engine.Engine, "before_cursor_execute")
def log_sql(conn, cursor, statement, parameters, context, executemany):
    QueryPool.queries.append(statement)


class TestCase:
    versioning_strategy = "subquery"
    transaction_column_name = "transaction_id"
    end_transaction_column_name = "end_transaction_id"
    composite_pk = False
    plugins = [TransactionChangesPlugin(), TransactionMetaPlugin()]
    transaction_cls = TransactionFactory()
    user_cls = None
    should_create_models = True

    def get_default_versioning_options(self, decl_base):
        return {
            "create_models": self.should_create_models,
            "base_classes": (decl_base,),
            "strategy": self.versioning_strategy,
            "support_async": False,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    @pytest.fixture
    def versioning_options(self, decl_base):
        return self.get_default_versioning_options(decl_base)

    @pytest.fixture
    def decl_base(self):
        class Base(DeclarativeBase):
            pass

        return Base

    @pytest.fixture
    def setup_versioning(self, versioning_options):
        make_versioned(options=versioning_options, plugins=self.plugins)
        versioning_manager.transaction_cls = self.transaction_cls
        versioning_manager.user_cls = self.user_cls

    @pytest.fixture(autouse=True)
    def setup_models(self, setup_versioning, decl_base, versioning_options):
        self.create_models(decl_base=decl_base, versioning_options=versioning_options)
        configure_mappers()

        if hasattr(self, "Article"):
            with contextlib.suppress(ClassNotVersioned):
                self.ArticleVersion = version_class(self.Article)
        if hasattr(self, "Tag"):
            with contextlib.suppress(ClassNotVersioned):
                self.TagVersion = version_class(self.Tag)

        yield

        uow_leaks = versioning_manager.units_of_work
        session_map_leaks = versioning_manager.session_connection_map

        remove_versioning()
        QueryPool.queries = []
        versioning_manager.reset()
        close_all_sessions()

        assert not uow_leaks
        assert not session_map_leaks

    @pytest.fixture
    def connection(self, setup_models, engine):
        connection = engine.connect()
        yield connection
        connection.close()

    @pytest.fixture
    def setup_tables(self, connection, decl_base):
        self.create_tables(connection=connection, decl_base=decl_base)
        yield
        self.drop_tables(connection=connection, decl_base=decl_base)

    @pytest.fixture
    def session(self, setup_tables, connection) -> t.Iterator[Session]:
        session_factory = sessionmaker(bind=connection)
        session = session_factory(autoflush=False, future=True)
        yield session
        session.rollback()
        session.expunge_all()
        session.close()

    def create_tables(self, connection, decl_base):
        with connection.begin():
            decl_base.metadata.create_all(connection)

    def drop_tables(self, connection, decl_base):
        with connection.begin():
            decl_base.metadata.drop_all(connection)

    def create_models(self, decl_base, versioning_options):
        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = copy(versioning_options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

            # Dynamic column cotaining all text content data
            fulltext_content = column_property(name + content + description)

        class Tag(decl_base):
            __tablename__ = "tag"
            __versioned__ = copy(versioning_options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = relationship(Article, backref="tags")

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
    combinations = [dict(zip(names, prod)) for prod in it.product(*(setting_variants[name] for name in names))]

    # Get the module where this function was called in.
    frm = inspect.stack()[1]
    module = inspect.getmodule(frm[0])

    class_suffix = base_class.__name__[0 : -len("TestCase")]
    for index, combination in enumerate(combinations):
        class_name = f"Test{class_suffix}{index}"
        # Assign a new test case class for current module.
        setattr(module, class_name, type(class_name, (base_class,), combination))
