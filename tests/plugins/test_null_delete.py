import sqlalchemy as sa

from sqlalchemy_history.plugins import NullDeletePlugin
from tests import TestCase


class DeleteTestCase(TestCase):
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


class TestDeleteWithoutStoreDataAtDelete(DeleteTestCase):
    plugins = [NullDeletePlugin()]

    def test_creates_versions_on_delete(self, session):
        self._delete(session)
        versions = session.scalars(sa.select(self.ArticleVersion)).all()
        assert len(versions) == 2
        assert versions[1].name is None
        assert versions[1].content is None
