from __future__ import annotations

import os

import sqlalchemy as sa
from pytest import mark
from sqlalchemy.orm import declarative_base

from tests import TestCase


@mark.skipif(
    os.environ.get("DB") == "sqlite",
    reason="sqlite doesn't have a concept of schema",
)
class TestCustomSchema(TestCase):
    def create_models(self):
        self.Model = declarative_base(metadata=sa.MetaData(schema="sqlahistory"))

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
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
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            name = sa.Column(sa.Unicode(255))

        Tag.articles = sa.orm.relationship(Article, secondary=article_tag, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def create_tables(self):
        try:
            self.connection.execute(sa.text("DROP SCHEMA IF EXISTS sqlahistory"))
            self.connection.execute(sa.text("CREATE SCHEMA sqlahistory"))
        except sa.exc.DatabaseError:
            try:
                # Create a User for Oracle DataBase as it does not have concept of schema
                # ref: https://stackoverflow.com/questions/10994414/missing-authorization-clause-while-creating-schema # noqa: E501
                self.connection.execute(sa.text("CREATE USER sqlahistory identified by sqlahistory"))
                # need to give privilege to create table to this new user
                # ref: https://stackoverflow.com/questions/27940522/no-privileges-on-tablespace-users
                self.connection.execute(sa.text("GRANT UNLIMITED TABLESPACE TO sqlahistory"))
            except sa.exc.DatabaseError as dbe:  # pragma: no cover
                if (
                    "ORA-01920: user name 'SQLAHISTORY' conflicts with another user or role name"
                    not in dbe.__str__()
                ):
                    # NOTE: prior to oracle 23c we don't have concept of if not exists
                    #       so we just try to create if fails we continue
                    raise
        finally:
            self.connection.commit()
        TestCase.create_tables(self)

    def test_version_relations(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        self.session.add(article)
        self.session.commit()
        assert article.versions[0].tags == []
