import sqlalchemy as sa
from sqlalchemy.orm import deferred

from sqlalchemy_history import count_versions, versioning_manager
from tests import TestCase


class TestInsert(TestCase):
    def _insert(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        return article

    def test_insert_creates_version(self, session):
        article = self._insert(session)
        version = article.versions.all()[-1]
        assert version.name == "Some article"
        assert version.content == "Some content"
        assert version.transaction.id == version.transaction_id

    def test_stores_operation_type(self, session):
        article = self._insert(session)
        assert article.versions[0].operation_type == 0

    def test_multiple_consecutive_flushes(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.flush()
        article2 = self.Article()
        article2.name = "Some article"
        article2.content = "Some content"
        session.add(article2)
        session.flush()
        session.commit()
        assert article.versions.count() == 1
        assert article2.versions.count() == 1


class TestInsertWithDeferredColumn(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = deferred(sa.Column(sa.Unicode(255)))

        self.TextItem = TextItem

    def test_insert(self, session):
        item = self.TextItem()
        session.add(item)
        session.commit()
        assert count_versions(item) == 1


class TestInsertNonVersionedObject(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = deferred(sa.Column(sa.Unicode(255)))

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = deferred(sa.Column(sa.Unicode(255)))

        self.TextItem = TextItem

    def test_does_not_create_transaction(self, session):
        item = self.TextItem()
        session.add(item)
        session.commit()

        assert session.scalar(sa.select(sa.func.count()).select_from(versioning_manager.transaction_cls)) == 0
