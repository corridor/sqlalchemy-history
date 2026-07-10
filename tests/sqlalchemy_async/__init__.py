import contextlib
import os
from copy import copy

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, close_all_sessions, create_async_engine
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
from tests import QueryPool, get_dns_from_driver


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

    @property
    def options(self):
        return {
            "create_models": self.should_create_models,
            "base_classes": (self.Model,),
            "strategy": self.versioning_strategy,
            "support_async": True,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    @pytest.fixture
    async def setup_declarative_base(self):
        class Base(AsyncAttrs, DeclarativeBase):
            pass

        self.Model = Base
        yield
        del self.Model

    @pytest.fixture
    async def setup_versioning(self, setup_declarative_base):
        make_versioned(options=self.options, plugins=self.plugins)
        versioning_manager.transaction_cls = self.transaction_cls
        versioning_manager.user_cls = self.user_cls

    @pytest.fixture
    async def setup_engine(self, setup_versioning, anyio_backend):
        if "DB" not in os.environ:  # pragma: no cover
            # NOTE: We set DB environment variable explicitly if someone has not provided as this value
            #       is used to skip other test cases and if one doesn't specifiy this value tests starts
            #       breaking. We don't cover this in coverage as our CI always
            #       specifies DB variable
            os.environ["DB"] = "sqlite"
        self.driver = os.environ.get("DB")
        self.engine = create_async_engine(get_dns_from_driver(self.driver, mode="async"))
        yield
        await self.engine.dispose()

    @pytest.fixture
    async def setup_models(self, setup_engine):
        self.create_models()
        configure_mappers()

    @pytest.fixture
    async def setup_tables(self, setup_models):
        if hasattr(self, "Article"):
            with contextlib.suppress(ClassNotVersioned):
                self.ArticleVersion = version_class(self.Article)
        if hasattr(self, "Tag"):
            with contextlib.suppress(ClassNotVersioned):
                self.TagVersion = version_class(self.Tag)
        await self.create_tables()
        yield
        await self.drop_tables()

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.Model.metadata.create_all)

    async def drop_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(self.Model.metadata.drop_all)

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

            fulltext_content = column_property(name + content + description)

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = relationship(Article, backref="tags")

        self.Article = Article
        self.Tag = Tag

    @pytest.fixture(autouse=True)
    async def setup_session(self, setup_tables):
        SessionLocal = async_sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
        self.session = SessionLocal()
        yield
        await self.session.rollback()
        uow_leaks = versioning_manager.units_of_work
        session_map_leaks = versioning_manager.session_connection_map

        remove_versioning()
        QueryPool.queries = []
        versioning_manager.reset()

        await close_all_sessions()
        self.session.expunge_all()

        assert not uow_leaks
        assert not session_map_leaks

    # Helper functions

    async def versions(self, parent):
        return (await self.session.scalars(parent.versions.select())).all()

    async def ordered_versions(self, version_model):
        return (
            await self.session.scalars(
                sa.select(version_model).order_by(getattr(version_model, self.options["transaction_column_name"]))
            )
        ).all()
