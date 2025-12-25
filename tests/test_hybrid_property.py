from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sqlalchemy_history.utils import version_class
from tests import TestCase


class TestHybridProperty(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            publish = sa.Column(sa.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

            author_id = sa.Column(sa.Integer, sa.ForeignKey("article_author.id"), nullable=False)

            @sa.ext.hybrid.hybrid_property
            def time_from_publish(self):
                return datetime.datetime.today() - self.publish

            @sa.ext.hybrid.hybrid_property
            def author_name(self):
                return self.author.name

            @author_name.expression
            def author_name(cls):
                return (
                    sa.select(ArticleAuthor.name).where(ArticleAuthor.id == cls.author_id).scalar_subquery()
                )

        class ArticleAuthor(self.Model):
            __tablename__ = "article_author"
            __versioned__ = {}

            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)
            articles = relationship("Article", backref="author")

        self.Article = Article

    def test_hybrid_property_mapping_for_versioned_class(self):
        version_class(self.Article).time_from_publish

    def test_version_class_hybrid_property_in_sql_expression(self):
        sa.select(version_class(self.Article).author_name)
