import os
import sqlalchemy as sa
from pytest import mark
from sqlalchemy.ext.declarative import declarative_base
from tests import TestCase


@mark.skipif("os.environ.get('DB') in ['sqlite', 'oracle']")
class TestCustomSchema(TestCase):
    def create_models(self):
        self.Model = declarative_base(metadata=sa.MetaData(schema="sqlahistory"))

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        article_tag = sa.Table(
            "article_tag",
            self.Model.metadata,
            sa.Column(
                "article_id",
                sa.Integer,
                sa.ForeignKey("article.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("tag_id", sa.Integer, sa.ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
        )

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        Tag.articles = sa.orm.relationship(Article, secondary=article_tag, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def create_tables(self):
        self.connection.execute("DROP SCHEMA IF EXISTS sqlahistory")
        self.connection.execute("CREATE SCHEMA sqlahistory")
        TestCase.create_tables(self)

    def test_version_relations(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        self.session.add(article)
        self.session.commit()
        assert article.versions[0].tags == []
