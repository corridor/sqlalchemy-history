import sqlalchemy as sa
from sqlalchemy_history import get_versioning_manager
from tests import TestCase


class ChangeSetBaseTestCase(TestCase):
    def test_changeset_for_insert(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        self.session.add(article)
        self.session.commit()
        assert article.versions[0].changeset == {
            "content": [None, "Some content"],
            "name": [None, "Some article"],
            "id": [None, 1],
        }

    def test_changeset_for_update(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        self.session.add(article)
        self.session.commit()

        article.name = "Updated name"
        article.content = "Updated content"
        self.session.commit()

        assert article.versions[1].changeset == {
            "content": ["Some content", "Updated content"],
            "name": ["Some article", "Updated name"],
        }


class ChangeSetTestCase(ChangeSetBaseTestCase):
    def test_changeset_for_history_that_does_not_have_first_insert(self):
        tx_log_class = get_versioning_manager(self.Article).transaction_cls
        tx_log = tx_log_class(issued_at=sa.func.now())

        self.session.add(tx_log)
        self.session.commit()

        self.session.execute(
            sa.text(
                """INSERT INTO article_version
            (id, %s, name, content, operation_type)
            VALUES
            (1, %d, 'something', 'some content', 1)
            """
                % (self.transaction_column_name, tx_log.id)
            )
        )

        assert self.session.query(self.ArticleVersion).first().changeset == {
            "content": [None, "some content"],
            "id": [None, 1],
            "name": [None, "something"],
        }


class TestChangeSetWithValidityStrategy(ChangeSetTestCase):
    versioning_strategy = "validity"


class TestChangeSetWithCustomTransactionColumn(ChangeSetTestCase):
    transaction_column_name = "tx_id"


class TestChangeSetWhenParentContainsAdditionalColumns(ChangeSetTestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = sa.orm.relationship(Article, backref="tags")

        subquery = sa.select(sa.func.count(Tag.id)).where(Tag.article_id == Article.id).correlate_except(Tag)
        subquery = subquery.scalar_subquery()
        Article.tag_count = sa.orm.column_property(subquery)

        self.Article = Article
        self.Tag = Tag
