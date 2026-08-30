from tests import TestCase


class TestSavepoints(TestCase):
    def test_flush_and_nested_rollback(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        session.flush()
        savepoint = session.begin_nested()
        session.add(self.Article(name="Some article"))
        article.name = "Updated name"
        savepoint.rollback()
        session.commit()
        assert article.versions.count() == 1
        assert article.versions.all()[-1].name == "Some article"

    def test_partial_rollback(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        savepoint = session.begin_nested()
        session.add(self.Article(name="Some article"))
        article.name = "Updated name"
        savepoint.rollback()
        session.commit()
        assert article.versions.count() == 1
        assert article.versions.all()[-1].name == "Some article"

    def test_multiple_savepoints(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        session.flush()
        savepoint = session.begin_nested()
        article.name = "Updated name"
        savepoint.commit()
        session.begin_nested()
        article.name = "Another article"
        session.commit()
        assert article.versions.count() == 1
        assert article.versions.all()[-1].name == "Another article"
