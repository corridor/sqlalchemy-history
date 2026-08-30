import pytest
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sqlalchemy_history.reverter import Reverter, ReverterException
from tests import TestCase


class TestReverter(TestCase):
    def test_raises_exception_for_unknown_relations(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)

        session.commit()
        version = article.versions[0]

        with pytest.raises(ReverterException):
            Reverter(version, relations=["unknown_relation"])


class RevertTestCase(TestCase):
    def add_article(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()
        return article

    def test_simple_revert(self, session):
        article = self.add_article(session)
        article.name = "Updated name"
        article.content = "Updated content"
        session.commit()
        session.refresh(article)
        article.versions[0].revert()
        assert article.name == "Some article"
        assert article.content == "Some content"

    def test_revert_deleted_model(self, session):
        article = self.add_article(session)
        old_article_id = article.id
        version = article.versions[0]
        session.delete(article)
        session.commit()
        version.revert()
        assert article.id == old_article_id
        assert article.name == "Some article"
        assert article.content == "Some content"

    def test_revert_deletion(self, session):
        article = self.add_article(session)
        old_article_id = article.id
        version = article.versions[0]
        session.delete(article)
        session.commit()
        version.revert()
        session.commit()
        assert session.scalar(sa.select(sa.func.count()).select_from(self.Article)) == 1
        article = session.get(self.Article, old_article_id)

        assert version.next.next

        version.next.revert()
        session.commit()
        assert not session.get(self.Article, old_article_id)

    def test_revert_version_with_one_to_many_relation(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        article.tags.append(self.Tag(name="some tag"))
        session.add(article)
        session.commit()
        article.name = "Updated name"
        article.content = "Updated content"
        article.tags = []
        session.commit()
        session.refresh(article)
        assert article.tags == []
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0].article
        article.versions[0].revert(relations=["tags"])
        session.commit()

        assert article.name == "Some article"
        assert article.content == "Some content"
        assert len(article.tags) == 1
        assert article.tags[0].name == "some tag"

    def test_with_one_to_many_relation_delete_newly_added(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        article.tags.append(self.Tag(name="some tag"))
        session.add(article)
        session.commit()
        article.name = "Updated name"
        article.content = "Updated content"
        article.tags.append(self.Tag(name="some other tag"))
        session.add(article)
        session.commit()
        session.refresh(article)
        assert len(article.tags) == 2
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0].article
        article.versions[0].revert(relations=["tags"])
        session.commit()

        assert article.name == "Some article"
        assert article.content == "Some content"
        assert len(article.tags) == 1
        assert article.tags[0].name == "some tag"

    def test_with_one_to_many_relation_resurrect_deleted(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        tag = self.Tag(name="some other tag")
        article.tags.append(self.Tag(name="some tag"))
        article.tags.append(tag)
        session.add(article)
        session.commit()
        article.name = "Updated name"
        article.tags.remove(tag)
        session.add(article)
        session.commit()
        session.refresh(article)
        assert len(article.tags) == 1
        assert len(article.versions[0].tags) == 2
        article.versions[0].revert(relations=["tags"])
        session.commit()
        assert len(article.tags) == 2
        assert article.tags[0].name == "some tag"

    @pytest.mark.filterwarnings("error::sqlalchemy.exc.SAWarning")
    def test_revert_with_nested_transaction_warning(self, session):
        article = self.Article(name="Some article")
        session.add(article)
        session.commit()
        session.begin_nested()
        article.name = "Updated name"
        session.commit()
        assert article.versions.count() == 2
        assert article.versions.all()[-1].name == "Updated name"


class TestRevertWithDefaultVersioningStrategy(RevertTestCase):
    pass


class TestRevertWithValidityVersioningStrategy(RevertTestCase):
    versioning_strategy = "validity"


class TestRevertWithCustomTransactionColumn(RevertTestCase):
    transaction_column_name = "tx_id"


class TestRevertWithColumnExclusion(RevertTestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"exclude": ["description"]}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        self.Article = Article

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = relationship(Article, backref="tags")

        self.Article = Article
        self.Tag = Tag
