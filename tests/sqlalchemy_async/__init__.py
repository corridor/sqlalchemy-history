import contextlib
import typing as t
from copy import copy

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, close_all_sessions
from sqlalchemy.orm import DeclarativeBase, column_property, configure_mappers, relationship

from sqlalchemy_history import (
    ClassNotVersioned,
    make_versioned,
    remove_versioning,
    version_class,
    versioning_manager,
)
from sqlalchemy_history.plugins import TransactionChangesPlugin, TransactionMetaPlugin
from sqlalchemy_history.transaction import TransactionFactory
from tests import QueryPool


class AsyncTestCase:
    versioning_strategy = "subquery"
    transaction_column_name = "transaction_id"
    end_transaction_column_name = "end_transaction_id"
    composite_pk = False
    plugins = [TransactionChangesPlugin(), TransactionMetaPlugin()]
    transaction_cls = TransactionFactory()
    user_cls = None
    should_create_models = True
    async_database_url = "sqlite+aiosqlite:///:memory:"

    @classmethod
    def get_default_versioning_options(cls, decl_base):
        return {
            "create_models": cls.should_create_models,
            "base_classes": (decl_base,),
            "strategy": cls.versioning_strategy,
            "support_async": True,
            "transaction_column_name": cls.transaction_column_name,
            "end_transaction_column_name": cls.end_transaction_column_name,
        }

    @pytest.fixture(scope="class")
    @classmethod
    def versioning_options(cls, decl_base):
        return cls.get_default_versioning_options(decl_base)

    @pytest.fixture(scope="class")
    @classmethod
    async def decl_base(cls):
        class Base(AsyncAttrs, DeclarativeBase):
            pass

        return Base

    @pytest.fixture(scope="class")
    @classmethod
    async def setup_versioning(cls, versioning_options):
        make_versioned(options=versioning_options, plugins=cls.plugins)
        versioning_manager.transaction_cls = cls.transaction_cls
        versioning_manager.user_cls = cls.user_cls

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    async def setup_models(cls, setup_versioning, decl_base, versioning_options):
        model_owner = cls()
        model_owner.create_models(decl_base=decl_base, versioning_options=versioning_options)
        for name, value in vars(model_owner).items():
            setattr(cls, name, value)
        configure_mappers()

        if hasattr(cls, "Article"):
            with contextlib.suppress(ClassNotVersioned):
                cls.ArticleVersion = version_class(cls.Article)
        if hasattr(cls, "Tag"):
            with contextlib.suppress(ClassNotVersioned):
                cls.TagVersion = version_class(cls.Tag)

        yield

        remove_versioning()
        versioning_manager.reset()

    @pytest.fixture(autouse=True)
    async def cleanup_test_state(self, setup_models):
        yield

        uow_leaks = versioning_manager.units_of_work
        session_map_leaks = versioning_manager.session_connection_map

        QueryPool.queries = []
        await close_all_sessions()

        assert not uow_leaks
        assert not session_map_leaks

    @pytest.fixture(scope="class", autouse=True)
    @classmethod
    async def setup_tables(cls, request, setup_models, async_engine, decl_base):
        # Keep classes containing only mapper-level tests from touching the database.
        test_items = (item for item in request.session.items if item.cls is request.cls)
        if not any("async_session" in item.fixturenames for item in test_items):
            yield
            return

        table_owner = cls()
        await table_owner.create_tables(async_engine, decl_base)
        yield
        await table_owner.drop_tables(async_engine, decl_base)

    async def create_tables(self, async_engine, decl_base):
        async with async_engine.begin() as conn:
            await conn.run_sync(decl_base.metadata.create_all)

    async def drop_tables(self, async_engine, decl_base):
        async with async_engine.begin() as conn:
            await conn.run_sync(decl_base.metadata.drop_all)

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

    @pytest.fixture
    async def async_session(self, setup_tables, async_engine) -> t.AsyncIterator[AsyncSession]:
        connection = await async_engine.connect()
        transaction = await connection.begin()
        # Test commits must not commit the fixture-owned isolation transaction.
        session_factory = async_sessionmaker(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="rollback_only",
        )
        session = session_factory()
        yield session
        await session.rollback()
        session.expunge_all()
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()

    # Helper functions

    async def versions(self, session, parent):
        return (await session.scalars(parent.versions.select())).all()

    async def ordered_versions(self, session, versioning_options, version_model):
        return (
            await session.scalars(
                sa.select(version_model).order_by(getattr(version_model, versioning_options["transaction_column_name"]))
            )
        ).all()
