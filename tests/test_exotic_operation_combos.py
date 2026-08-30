from sqlalchemy_history.operation import Operation
from tests import TestCase, create_test_cases


class ExoticOperationCombosTestCase(TestCase):
    def test_insert_deleted_object(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.flush()
        session.commit()

        session.delete(article)
        article2 = self.Article(id=article.id, name="Some article 2")
        session.add(article2)
        session.commit()
        assert article2.versions.count() == 2
        assert article2.versions[0].operation_type == Operation.INSERT
        assert article2.versions[1].operation_type == Operation.UPDATE

    def test_insert_deleted_and_flushed_object(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        assert article.versions.count()

        session.delete(article)
        session.flush()
        assert article.versions.count() == 2
        article2 = self.Article(id=article.id, name="Some other article")
        session.add(article2)
        session.commit()
        assert article2.versions.count() == 2
        assert article2.versions[0].operation_type == Operation.INSERT
        assert article2.versions[1].operation_type == Operation.UPDATE

    def test_replace_deleted_object_with_update(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        article2 = self.Article()
        article2.name = "Another article"
        article2.content = "Some other content"
        session.add(article)
        session.add(article2)
        session.commit()

        session.delete(article)
        session.flush()

        article2.name = article.name
        session.commit()
        assert article2.versions.count() == 2
        assert article2.versions[0].operation_type == Operation.INSERT
        assert article2.versions[1].operation_type == Operation.UPDATE

    def test_insert_flushed_object(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.flush()
        session.commit()

        assert article.versions.count() == 1
        assert article.versions[0].operation_type == Operation.INSERT


# Skip the tests until SQLAlchemy has renewed its UOW handling:
create_test_cases(ExoticOperationCombosTestCase)
