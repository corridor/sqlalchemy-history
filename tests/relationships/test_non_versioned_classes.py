from copy import copy

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from tests import TestCase


class TestRelationshipToNonVersionedClass(TestCase):
    def create_models(self, decl_base, versioning_options):
        class User(decl_base):
            __tablename__ = "user"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = copy(versioning_options)

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            author_id = sa.Column(sa.Integer, sa.ForeignKey(User.id))
            author = relationship(User)

        self.Article = Article
        self.User = User

    def test_single_insert(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        article.author = user
        session.add(article)
        session.commit()

        assert isinstance(article.versions[0].author, self.User)

    def test_change_relationship(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        user = self.User(name="Some user")
        session.add(article)
        session.add(user)
        session.commit()

        assert article.versions.count() == 1
        article.author = user
        session.commit()
        assert article.versions.count() == 2


class TestManyToManyRelationshipToNonVersionedClass(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (decl_base,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        article_tag = sa.Table(
            "article_tag",
            decl_base.metadata,
            sa.Column(
                "article_id",
                sa.Integer,
                sa.ForeignKey("article.id"),
                primary_key=True,
            ),
            sa.Column("tag_id", sa.Integer, sa.ForeignKey("tag.id"), primary_key=True),
        )

        class Tag(decl_base):
            __tablename__ = "tag"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        Tag.articles = relationship(Article, secondary=article_tag, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def test_single_insert(self, session):
        article = self.Article()
        article.name = "Some article"
        article.content = "Some content"
        tag = self.Tag(name="some tag")
        article.tags.append(tag)
        session.add(article)
        session.commit()
        assert len(article.versions[0].tags) == 1
        assert isinstance(article.versions[0].tags[0], self.Tag)

    def test_no_cartesian_product_with_multiple_unrelated_tags(self, session):
        # Create an article with one tag
        article = self.Article(name="Some article")
        tag1 = self.Tag(name="tag1")
        article.tags.append(tag1)
        session.add(article)
        session.commit()

        # Create another article with a different tag
        article2 = self.Article(name="Another article")
        tag2 = self.Tag(name="tag2")
        article2.tags.append(tag2)
        session.add(article2)
        session.commit()

        # Ensure the first article's version only has its own tag, not all tags
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0] == tag1
