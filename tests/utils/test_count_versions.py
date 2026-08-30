from sqlalchemy_history import count_versions
from tests import TestCase


class TestCountVersions(TestCase):
    def test_count_versions_without_versions(self):
        article = self.Article(name="Some article")
        assert count_versions(article) == 0

    def test_count_versions_with_initial_version(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        session.commit()
        assert count_versions(article) == 1

    def test_count_versions_with_multiple_versions(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        session.commit()
        article.name = "Updated article"
        session.commit()
        assert count_versions(article) == 2

    def test_count_versions_with_multiple_objects(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        article2 = self.Article(name="Some article")
        session.add(article2)
        session.commit()
        assert count_versions(article) == 1
