import pytest

from tests import TestCase


class TestSavepoints(TestCase):
    def test_flush_and_nested_rollback(self):
        article = self.Article(name="Some article")
        self.session.add(article)
        self.session.flush()
        self.session.begin_nested()
        self.session.add(self.Article(name="Some article"))
        article.name = "Updated name"
        self.session.rollback()
        self.session.commit()
        assert article.versions.count() == 1
        assert article.versions[-1].name == "Some article"

    def test_partial_rollback(self):
        article = self.Article(name="Some article")
        self.session.add(article)
        self.session.begin_nested()
        self.session.add(self.Article(name="Some article"))
        article.name = "Updated name"
        self.session.rollback()
        self.session.commit()
        assert article.versions.count() == 1
        assert article.versions[-1].name == "Some article"

    def test_multiple_savepoints(self):
        if self.driver == "sqlite":
            pytest.skip()

        article = self.Article(name="Some article")
        self.session.add(article)
        self.session.flush()
        self.session.begin_nested()
        article.name = "Updated name"
        self.session.commit()
        self.session.begin_nested()
        article.name = "Another article"
        self.session.commit()
        self.session.commit()
        assert article.versions.count() == 1
        assert article.versions[-1].name == "Another article"
