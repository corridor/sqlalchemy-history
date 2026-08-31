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

    def get_default_versioning_options(self, decl_base):
        return {
            "create_models": self.should_create_models,
            "base_classes": (decl_base,),
            "strategy": self.versioning_strategy,
            "support_async": True,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    @pytest.fixture
    def versioning_options(self, decl_base):
        return self.get_default_versioning_options(decl_base)

    @pytest.fixture
    async def decl_base(self):
        class Base(AsyncAttrs, DeclarativeBase):
            pass

        return Base

    @pytest.fixture
    async def setup_versioning(self, versioning_options):
        make_versioned(options=versioning_options, plugins=self.plugins)
        versioning_manager.transaction_cls = self.transaction_cls
        versioning_manager.user_cls = self.user_cls

    @pytest.fixture(autouse=True)
    async def setup_models(self, setup_versioning, decl_base, versioning_options):
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
        await close_all_sessions()

        assert not uow_leaks
        assert not session_map_leaks

    @pytest.fixture
    async def setup_tables(self, setup_models, async_engine, decl_base):
        await self.create_tables(async_engine, decl_base)
        yield
        await self.drop_tables(async_engine, decl_base)

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
        session_factory = async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)
        session = session_factory()
        yield session
        await session.rollback()
        session.expunge_all()
        await session.close()

    # Helper functions

    async def versions(self, session, parent):
        return (await session.scalars(parent.versions.select())).all()

    async def ordered_versions(self, session, versioning_options, version_model):
        return (
            await session.scalars(
                sa.select(version_model).order_by(getattr(version_model, versioning_options["transaction_column_name"]))
            )
        ).all()
