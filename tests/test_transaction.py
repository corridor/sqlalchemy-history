from __future__ import annotations

import os
import time

import pytest
import sqlalchemy as sa

from sqlalchemy_history import versioning_manager
from sqlalchemy_history.plugins import TransactionMetaPlugin
from tests import TestCase


class TestTransaction(TestCase):
    @pytest.fixture(autouse=True)
    def setup_method_for_transaction(self, setup_session):
        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        self.article.tags.append(self.Tag(name="Some tag"))
        self.session.add(self.article)
        self.session.commit()
        yield
        self.session.expunge(self.article)
        del self.article

    def test_relationships(self):
        assert self.article.versions[0].transaction

    def test_only_saves_transaction_if_actual_modifications(self):
        self.article.name = "Some article"
        self.session.commit()
        self.article.name = "Some article"
        self.session.commit()
        assert self.session.query(versioning_manager.transaction_cls).count() == 1

    def test_repr(self):
        transaction = self.session.query(versioning_manager.transaction_cls).first()
        assert f"<Transaction id={transaction.id}, issued_at={transaction.issued_at!r}>" == repr(transaction)

    def test_changed_entities(self):
        article_v0 = self.article.versions[0]
        transaction = article_v0.transaction
        assert transaction.changed_entities == {
            self.ArticleVersion: [article_v0],
            self.TagVersion: [self.article.tags[0].versions[0]],
        }

    def test_transaction_issued_at(self):
        time.sleep(1)
        self.article.name = "Some article 2"
        self.session.add(self.article)
        self.session.commit()
        assert (
            self.article.versions[0].transaction.issued_at != self.article.versions[1].transaction.issued_at
        )


# Check that the tests pass without TransactionChangesPlugin
class TestTransactionWithoutChangesPlugin(TestTransaction):
    plugins = [TransactionMetaPlugin()]


class TestAssigningUserClass(TestCase):
    user_cls = "User"

    def create_models(self):
        class User(self.Model):
            __tablename__ = "user"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(sa.Unicode(255), primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)

        self.User = User

    def test_copies_primary_key_type_from_user_class(self):
        attr = versioning_manager.transaction_cls.user_id
        assert isinstance(attr.property.columns[0].type, sa.Unicode)


@pytest.mark.skipif(
    os.environ.get("DB") in ["sqlite", "oracle"],
    reason="sqlite doesn't have a concept of schema for oracle refer below mentioned fixme!",
)
class TestAssigningUserClassInOtherSchema(TestCase):
    user_cls = "User"

    def create_models(self):
        class User(self.Model):
            __tablename__ = "user"
            __versioned__ = {"base_classes": (self.Model,)}
            __table_args__ = {"schema": "other"}

            id = sa.Column(sa.Unicode(255), primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)

        self.User = User

    def create_tables(self):
        try:
            self.connection.execute(sa.text("DROP SCHEMA IF EXISTS other"))
            self.connection.execute(sa.text("CREATE SCHEMA other"))
        except sa.exc.DatabaseError:  # pragma: no cover
            try:
                # Create a User for Oracle DataBase as it does not have concept of schema
                # ref: https://stackoverflow.com/questions/10994414/missing-authorization-clause-while-creating-schema # noqa: E501
                self.connection.execute(sa.text("CREATE USER other identified by other"))
                # need to give privilege to create table to this new user
                # ref: https://stackoverflow.com/questions/27940522/no-privileges-on-tablespace-users
                self.connection.execute(sa.text("grant all privileges TO other"))
                # FIXME: (cx_Oracle.DatabaseError) ORA-01031: insufficient privileges
                #        it seems system doesn't have privilege to conenct to other
                #        now when transaction tries to refer other.user is says insufficient table
                #        but same tests passes in test_table_builder?
                #        skipping for now
                # E       sqlalchemy.exc.DatabaseError: (cx_Oracle.DatabaseError) ORA-01031: insufficient privileges # noqa: E501
                # E       [SQL:
                # E       CREATE TABLE transaction (
                # E               issued_at DATE,
                # E               id NUMBER(19) NOT NULL,
                # E               remote_addr VARCHAR2(50 CHAR),
                # E               user_id VARCHAR2(255 CHAR),
                # E               PRIMARY KEY (id),
                # E               FOREIGN KEY(user_id) REFERENCES other."user" (id)
                # E       )
                # E
                # E       ]
            except sa.exc.DatabaseError as dbe:
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

    def test_can_build_transaction_model(self):
        # If create_models didn't crash this should be good
        pass
