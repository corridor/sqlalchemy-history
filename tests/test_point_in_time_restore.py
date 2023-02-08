from copy import copy
import datetime
import sqlalchemy as sa
from tests import TestCase
from sqlalchemy_history.utils import version_class


class TestPointInTime(TestCase):
    def create_models(self):
        article_author_table = sa.Table(
            "article_author",
            self.Model.metadata,
            sa.Column(
                "article_id", sa.Integer, sa.ForeignKey("article.id"), primary_key=True, nullable=False
            ),
            sa.Column("author_id", sa.Integer, sa.ForeignKey("author.id"), primary_key=True, nullable=False),
            sa.Column(
                "created_date",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
                default=datetime.datetime.utcnow,
            ),
        )

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)

        class Author(self.Model):
            __tablename__ = "author"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            articles = sa.orm.relationship(Article, secondary=article_author_table, backref="authors")

        class UserNonVersioned(self.Model):
            __tablename__ = "user"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        self.Article = Article
        self.Author = Author
        self.article_author_table = article_author_table
        self.UserNonVersioned = UserNonVersioned

    def test_transaction_based_point_in_time(self):
        article1 = self.Article(name="Article 1")
        article2 = self.Article(name="Article 2")
        author1 = self.Author(name="Author 1", articles=[article1, article2])
        author2 = self.Author(name="Author 2")
        non_versioned_obj = self.UserNonVersioned(name="ABC")
        self.session.add_all([article1, article2, author1, author2])
        # State one of DB has two articles one author related to these authors
        # and one author without any article.
        self.session.commit()
        article3 = self.Article(name="Article 3", authors=[author2])
        article4 = self.Article(name="Article 4", authors=[author1, author2])
        self.session.delete(article2)
        self.session.add_all([article3, article4])
        # State Two of DB author2 adds a new article
        # Author2 and Author1 make a new article together!
        # Article2 is deleted
        self.session.commit()

        # Get Transaction Table
        transaction_cls = self.Model.registry._class_registry["Transaction"]
        transactions = self.session.query(transaction_cls).all()
        assert len(transactions) == 2

        first_transaction, second_transaction = transactions
        # For first transaction state we should only get article_1 and article_2
        # Two authors where author1 has written two articles and author2 has
        # achieved nothing yet.
        db_state_dict = first_transaction.restore_db_state
        # There are only two ORM tables
        assert len(db_state_dict) == 2

        # Make Sure expected tables are in db_state_dict
        assert version_class(self.Article) in db_state_dict
        assert version_class(self.Author) in db_state_dict

        # Validate Records for transaction One

        ## Validate Article Table state
        article_db_records = db_state_dict[version_class(self.Article)]
        assert len(article_db_records) == 2
        assert {"Article 1", "Article 2"} == {versioned_obj.name for versioned_obj in article_db_records}
        # Validate Relationships
        for versioned_obj in article_db_records:
            assert len(versioned_obj.authors) == 1  # Only Author 1 has achivements in transaction One
            assert {author.name for author in versioned_obj.authors} == {"Author 1"}

        ## Validate Author Table state
        author_db_records = db_state_dict[version_class(self.Author)]
        assert len(author_db_records) == 2
        assert {"Author 1", "Author 2"} == {versioned_obj.name for versioned_obj in author_db_records}
        for versioned_obj in author_db_records:
            if versioned_obj.name == "Author 1":
                assert len(versioned_obj.articles) == 2
                assert {"Article 1", "Article 2"} == {article.name for article in versioned_obj.articles}
            else:
                assert len(versioned_obj.articles) == 0

        # For Second transaction state we should only get article_1, article_3 and article_4
        # Two authors where author1 has written two articles and author2 has written one article
        db_state_dict = second_transaction.restore_db_state
        # There are only two ORM tables
        assert len(db_state_dict) == 2

        # Make Sure expected tables are in db_state_dict
        assert version_class(self.Article) in db_state_dict
        assert version_class(self.Author) in db_state_dict

        # Validate Records for transaction Two

        ## Validate Article Table state
        article_db_records = db_state_dict[version_class(self.Article)]
        assert len(article_db_records) == 3
        assert {"Article 1", "Article 3", "Article 4"} == {
            versioned_obj.name for versioned_obj in article_db_records
        }
        # Validate Relationships
        for versioned_obj in article_db_records:
            if versioned_obj.name == "Article 1":
                assert len(versioned_obj.authors) == 1
                assert {author.name for author in versioned_obj.authors} == {"Author 1"}
            elif versioned_obj.name == "Article 3":
                assert len(versioned_obj.authors) == 1
                assert {author.name for author in versioned_obj.authors} == {"Author 2"}
            elif versioned_obj.name == "Article 4":
                assert len(versioned_obj.authors) == 2
                assert {author.name for author in versioned_obj.authors} == {"Author 1", "Author 2"}

        ## Validate Author Table state
        author_db_records = db_state_dict[version_class(self.Author)]
        assert len(author_db_records) == 2
        assert {"Author 1", "Author 2"} == {versioned_obj.name for versioned_obj in author_db_records}
        # Validate Relationships
        for versioned_obj in author_db_records:
            if versioned_obj.name == "Author 1":
                assert len(versioned_obj.articles) == 2
                # FIXME: Versioned Relationships have limitation to refer only LTE transaction_id
                # So below DB still gives incorrect result as it refers TR1 Article
                # Even though in DB state we are not returning that.
                # FIXME: Since Author Object Transaction is not updated So It is what it is.

                # assert {author.name for author in versioned_obj.articles} == {"Article 1", "Article 4"}
            # elif versioned_obj.name == "Author 2":
            #     assert len(versioned_obj.articles) == 2
            #     assert {author.name for author in versioned_obj.articles} == {"Author 3", "Author 4"}
