import sqlalchemy as sa
from sqlalchemy.orm import deferred

from tests import TestCase


class TestDelete(TestCase):
    def _delete(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        session.delete(article)
        session.commit()

    def test_stores_operation_type(self, session):
        self._delete(session)
        versions = session.scalars(sa.select(self.ArticleVersion)).all()
        assert versions[1].operation_type == 2

    def test_creates_versions_on_delete(self, session):
        self._delete(session)
        versions = session.scalars(sa.select(self.ArticleVersion)).all()
        assert len(versions) == 2
        assert versions[1].name == "Some article"
        assert versions[1].content == "Some content"


class TestDeleteWithDeferredColumn(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = deferred(sa.Column(sa.Unicode(255)))

        self.TextItem = TextItem

    def test_insert_and_delete(self, session):
        item = self.TextItem()
        session.add(item)
        session.commit()
        session.delete(item)
        session.commit()
