from copy import copy
from tests import TestCase
import sqlalchemy as sa


class TestRelationshipToNonVersionedClass(TestCase):
    def create_models(self):
        class User(self.Model):
            __tablename__ = "user"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = copy(self.options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
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

        assert isinstance(article.versions[0].author, self.User)

    def test_change_relationship(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        self.session.add(article)
        self.session.add(user)
        self.session.commit()

        assert article.versions.count() == 1
        article.author = user
        self.session.commit()
        assert article.versions.count() == 2


class TestManyToManyRelationshipToNonVersionedClass(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        article_tag = sa.Table(
            "article_tag",
            self.Model.metadata,
            sa.Column(
                "article_id",
                sa.Integer,
                sa.ForeignKey("article.id"),
                primary_key=True,
            ),
            sa.Column("tag_id", sa.Integer, sa.ForeignKey("tag.id"), primary_key=True),
        )

        class Tag(self.Model):
            __tablename__ = "tag"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        Tag.articles = sa.orm.relationship(Article, secondary=article_tag, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def test_single_insert(self):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        tag = self.Tag(name="some tag")
        article.tags.append(tag)
        self.session.add(article)
        self.session.commit()
        assert len(article.versions[0].tags) == 1
        assert isinstance(article.versions[0].tags[0], self.Tag)

    def test_no_cartesian_product_with_multiple_unrelated_tags(self):
        # Create an article with one tag
        article = self.Article(name="Some article")
        tag1 = self.Tag(name="tag1")
        article.tags.append(tag1)
        self.session.add(article)
        self.session.commit()

        # Create another article with a different tag
        article2 = self.Article(name="Another article")
        tag2 = self.Tag(name="tag2")
        article2.tags.append(tag2)
        self.session.add(article2)
        self.session.commit()

        # Ensure the first article's version only has its own tag, not all tags
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0] == tag1
