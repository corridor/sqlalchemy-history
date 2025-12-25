from __future__ import annotations

import os
from copy import copy
from datetime import datetime

import pytest
import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase


class TestTableBuilder(TestCase):
    def test_assigns_foreign_keys_for_versions(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        article.tags.append(self.Tag(name="some tag"))
        self.session.add(article)
        self.session.commit()
        cls = version_class(self.Tag)
        version = self.session.query(cls).first()
        assert version.name == "some tag"
        assert version.id == 1
        assert version.article_id == 1

    def test_versioned_table_structure(self):
        table = version_class(self.Article).__table__
        assert "id" in table.c
        assert "name" in table.c
        assert "content" in table.c
        assert "description" in table.c
        assert "transaction_id" in table.c
        assert "operation_type" in table.c

    def test_removes_autoincrementation(self):
        table = version_class(self.Article).__table__
        assert table.c.id.autoincrement is False

    def test_removes_not_null_constraints(self):
        assert self.Article.__table__.c.name.nullable is False
        table = version_class(self.Article).__table__
        assert table.c.name.nullable is True

    def test_primary_keys_remain_not_nullable(self):
        assert self.Article.__table__.c.name.nullable is False
        table = version_class(self.Article).__table__
        assert table.c.id.nullable is False

    def test_transaction_id_column_not_nullable(self):
        assert self.Article.__table__.c.name.nullable is False
        table = version_class(self.Article).__table__
        assert table.c.transaction_id.nullable is False


class TestTableBuilderWithOnUpdate(TestCase):
    def create_models(self):
        options = copy(self.options)
        options["include"] = [
            "last_update",
        ]

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = options

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            last_update = sa.Column(
                sa.DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
                nullable=False,
            )

        self.Article = Article

    def test_takes_out_onupdate_triggers(self):
        table = version_class(self.Article).__table__
        assert table.c.last_update.onupdate is None

    def test_takes_out_default_triggers(self):
        table = version_class(self.Article).__table__
        assert table.c.last_update.default is None


@pytest.mark.skipif(os.environ.get("DB") == "sqlite", reason="sqlite doesn't have a concept of schema")
class TestTableBuilderInOtherSchema(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)
            __table_args__ = {"schema": "other"}

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )
            last_update = sa.Column(
                sa.DateTime,
                default=datetime.utcnow,
                onupdate=datetime.utcnow,
                nullable=False,
            )
            enum_col = sa.Column(sa.Enum("TYPE_A", "TYPE_B", name="test_enum"))

        self.Article = Article

    def create_tables(self):
        try:
            self.connection.execute(sa.text("DROP SCHEMA IF EXISTS other"))
            self.connection.execute(sa.text("CREATE SCHEMA other"))
        except sa.exc.DatabaseError:
            try:
                # Create a User for Oracle DataBase as it does not have concept of schema
                # ref: https://stackoverflow.com/questions/10994414/missing-authorization-clause-while-creating-schema # noqa: E501
                self.connection.execute(sa.text("CREATE USER other identified by other"))
                # need to give privilege to create table to this new user
                # ref: https://stackoverflow.com/questions/27940522/no-privileges-on-tablespace-users
                self.connection.execute(sa.text("GRANT UNLIMITED TABLESPACE TO other"))
            except sa.exc.DatabaseError as dbe:  # pragma: no cover
                if (
                    "ORA-01920: user name 'OTHER' conflicts with another user or role name"
                    not in dbe.__str__()
                ):
                    # NOTE: prior to oracle 23c we don't have concept of if not exists
                    #       so we just try to create if fails we continue
                    raise
        finally:
            self.connection.commit()
        TestCase.create_tables(self)

    def test_created_tables_retain_schema(self):
        table = version_class(self.Article).__table__
        assert table.schema is not None
        assert table.schema == self.Article.__table__.schema


class TestEnumNaming(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                autoincrement=True,
                primary_key=True,
            )

            enum_col = sa.Column(sa.Enum("TYPE_A", "TYPE_B", name="test_enum"))

        self.Article = Article

    def test_name_enums(self):
        version_model = version_class(self.Article)
        assert version_model.enum_col.type.name == "history_test_enum"
