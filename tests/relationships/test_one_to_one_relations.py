from copy import copy
from tests import TestCase, create_test_cases
from sqlalchemy_history import versioning_manager
import sqlalchemy as sa


class OneToOneRelationshipsTestCase(TestCase):
    def create_models(self):
        class User(self.Model):
            __tablename__ = "user"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            author_id = sa.Column(sa.Integer, sa.ForeignKey(User.id))
            author = sa.orm.relationship(User)

        self.Article = Article
        self.User = User

    def test_single_insert(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        self.session.add(article)
        self.session.commit()

        assert article.versions[0].author

    def test_multiple_relation_versions(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        self.session.add(article)
        self.session.commit()

        user.name = "Someone else"
        self.session.commit()

        article.name = "Some article 2"
        self.session.commit()

        assert article.versions[0].author == user.versions[0]
        assert article.versions[1].author == user.versions[1]

    def test_multiple_consecutive_inserts_and_removes(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        self.session.add(article)
        self.session.commit()

        user.name = "Someone else"
        self.session.commit()

        article.name = "Updated article"
        article2 = self.Article(name="Article 2")
        self.session.add(article2)
        article2.author = user
        self.session.commit()

        assert article.versions[0].author == user.versions[0]
        assert article2.versions[0].author == user.versions[1]

    def test_replace(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        self.session.add(article)
        self.session.commit()
        other_user = self.User(name="Some other user")
        article.author = other_user
        self.session.commit()

        assert article.versions[0].author == user.versions[0]
        assert article.versions[1].author == other_user.versions[0]

    def test_unordered_transaction_id(self):
        # In some DBs - the sequence of IDs used for primary keys is not monotonic
        # This example is taken from: test_multiple_relation_versions

        def create_transaction(id):
            # Use this fucntion to explicitly create transaction records where the ID
            # is not in increasing order
            transaction = versioning_manager.unit_of_work(self.session).create_transaction(self.session)
            transaction.id = id

        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        self.session.add(article)
        create_transaction(id=4)
        self.session.commit()

        user.name = "Some user 2"
        create_transaction(id=3)
        self.session.commit()

        article.name = "Some article 2"
        create_transaction(id=2)
        self.session.commit()

        assert article.versions[0].author == user.versions[0]
        assert article.versions[1].author == user.versions[1]


create_test_cases(OneToOneRelationshipsTestCase)
