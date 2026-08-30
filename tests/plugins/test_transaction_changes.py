import sqlalchemy as sa

from sqlalchemy_history import version_class
from sqlalchemy_history.plugins import TransactionChangesPlugin
from tests import TestCase


class TestTransactionChanges(TestCase):
    plugins = [TransactionChangesPlugin()]

    def test_has_relation_to_changes(self, session):
        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        self.article.tags.append(self.Tag(name="Some tag"))
        session.add(self.article)
        session.commit()
        tx = self.article.versions[0].transaction
        assert tx.changes


class TestTransactionChangedEntities(TestCase):
    plugins = [TransactionChangesPlugin()]

    def test_change_single_entity(self, session):
        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        session.add(self.article)
        session.commit()
        tx = self.article.versions[0].transaction

        assert tx.changed_entities == {version_class(self.article.__class__): [self.article.versions[0]]}

    def test_change_multiple_entities(self, session):
        self.article = self.Article()
        self.article.name = "Some article"
        self.article.content = "Some content"
        self.article.tags.append(self.Tag(name="Some tag"))
        session.add(self.article)
        session.commit()
        tx = self.article.versions[0].transaction

        assert self.article.versions[0] in tx.changed_entities[self.ArticleVersion]
        assert self.article.tags[0].versions[0] in tx.changed_entities[self.TagVersion]

    def test_saves_changed_entity_names(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        tx = article.versions[0].transaction
        assert tx.changes[0].entity_name == "Article"

    def test_saves_only_modified_entity_names(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        session.add(article)
        session.commit()

        TransactionChanges = article.__versioned__["transaction_changes"]

        article.name = "Some article"
        session.commit()

        assert session.scalar(sa.select(sa.func.count()).select_from(TransactionChanges)) == 1
