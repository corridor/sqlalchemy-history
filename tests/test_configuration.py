from __future__ import annotations

import sqlalchemy as sa
from pytest import raises
from sqlalchemy.orm import declarative_base

from sqlalchemy_history import (
    ClassNotVersioned,
    ImproperlyConfigured,
    TableNotVersioned,
    TransactionFactory,
    version_class,
    versioning_manager,
)
from sqlalchemy_history.utils import version_table
from tests import TestCase


class TestVersionedModelWithoutVersioning(TestCase):
    def create_models(self):
        TestCase.create_models(self)

        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {"versioning": False}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )

        self.TextItem = TextItem

    def test_does_not_create_history_class(self):
        # Normal Class is Versioned
        assert version_class(self.Article).__name__ == "ArticleVersion"
        # If disabled Versioning doesn't happen for specific class
        with raises(ClassNotVersioned):
            version_class(self.TextItem)

    def test_does_not_create_history_table(self):
        assert version_table(self.Article.__table__).name == "article_version"
        with raises(TableNotVersioned):
            version_table(self.TextItem.__table__)

    def test_does_add_objects_to_unit_of_work(self):
        self.session.add(self.TextItem())
        self.session.commit()


class TestWithUnknownUserClass:
    def test_raises_improperly_configured_error(self):
        self.Model = declarative_base()

        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )

        self.TextItem = TextItem

        versioning_manager.user_cls = "User"
        versioning_manager.declarative_base = self.Model

        factory = TransactionFactory()
        with raises(ImproperlyConfigured):
            factory(versioning_manager)


class TestWithCreateModelsAsFalse(TestCase):
    should_create_models = False

    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        class Category(self.Model):
            __tablename__ = "category"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = sa.orm.relationship(Article, backref=sa.orm.backref("category", uselist=False))

        self.Article = Article
        self.Category = Category

    def test_does_not_create_models(self):
        with raises(ClassNotVersioned):
            version_class(self.Article)
        assert version_table(self.Article.__table__).name == "article_version"


class TestWithoutAnyVersionedModels(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        self.Article = Article

    def test_insert(self):
        article = self.Article(name="Some article")
        self.session.add(article)
        self.session.commit()
        assert not hasattr(article, "versions")
