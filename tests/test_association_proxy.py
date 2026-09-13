import pytest
import sqlalchemy as sa
from sqlalchemy.ext.associationproxy import AssociationProxy, AssociationProxyInstance, association_proxy
from sqlalchemy.orm import Session, backref, relationship

from sqlalchemy_history.reverter import Reverter, ReverterException
from sqlalchemy_history.utils import get_association_proxies, version_class
from tests import TestCase


class TestAssociationProxy(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Category(decl_base):
            __tablename__ = "category"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)

        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            category_id = sa.Column(sa.Integer, sa.ForeignKey(Category.id))
            category = relationship(Category, backref="articles")

            upanaam = association_proxy("tags", "name")

        class Tag(decl_base):
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
        self.Category = Category

    def test_association_proxy_mapping(self):
        assoc_mapping = get_association_proxies(self.Article)
        assert len(assoc_mapping) == 1
        assert next(iter(assoc_mapping.keys())) == "upanaam"
        assert isinstance(assoc_mapping["upanaam"], AssociationProxy)

    def test_association_proxy_detection(self):
        """
        Currently Versioned Model have a proxy mapped as a property due limitation in the way relationships
         are handled, For now a property in versioned model should be available for proxy attributes of
         orginal model
        """
        assert issubclass(type(self.Article.upanaam), AssociationProxyInstance)
        assert isinstance(version_class(self.Article).upanaam, property)

    def test_association_proxy_retrieval(self, session):
        tag = self.Tag(name="tag1")
        article = self.Article(name="article1", tags=[tag])
        session.add(article)
        session.commit()
        tag2 = self.Tag(name="tag2")
        session.add(tag2)
        article.tags += [tag2]
        article.name = "updated"
        session.add(article)
        session.commit()
        assert article.versions.count() == 2
        assert len(article.versions.all()[0].tags) == 1
        assert len(article.versions.all()[1].tags) == 2
        assert set(article.versions.all()[0].upanaam) == {"tag1"}
        assert set(article.versions.all()[1].upanaam) == {"tag1", "tag2"}

    def test_revert_collection_association_proxy(self, session: Session):
        tag = self.Tag(name="tag1")
        article = self.Article(name="article1", tags=[tag])
        session.add(article)
        session.commit()

        tag.name = "renamed"
        article.tags.append(self.Tag(name="tag2"))
        session.commit()

        article.versions[0].revert(relations=["upanaam"])
        session.commit()

        assert article.name == "article1"
        assert article.upanaam == ["tag1"]

    def test_revert_deduplicates_proxy_and_relationship(self, session: Session):
        article = self.Article(name="article1", tags=[self.Tag(name="tag1")])
        session.add(article)
        session.commit()

        reverter = Reverter(article.versions[0], relations=["upanaam", "tags"])

        assert reverter.relations == ["tags"]

    def test_revert_nested_association_proxy(self, session: Session):
        article = self.Article(name="article1", tags=[self.Tag(name="tag1")])
        category = self.Category(name="category1", articles=[article])
        session.add(category)
        session.commit()

        category.name = "updated"
        article.tags[0].name = "renamed"
        article.tags.append(self.Tag(name="tag2"))
        session.commit()

        category.versions[0].revert(relations=["articles.upanaam"])
        session.commit()

        assert category.name == "category1"
        assert article.upanaam == ["tag1"]

    def test_revert_proxy_with_invalid_target_relationship(self, session: Session):
        article = self.Article(name="article1")
        session.add(article)
        session.commit()
        self.Article.invalid_proxy = association_proxy("missing", "name")

        with pytest.raises(
            ReverterException,
            match=r"Association proxy 'invalid_proxy'.*targets 'missing', which is not a relationship",
        ):
            Reverter(article.versions[0], relations=["invalid_proxy"])


class TestScalarAssociationProxyRevert(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            summary = association_proxy("details", "summary")

        class ArticleDetails(decl_base):
            __tablename__ = "article_details"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id), nullable=False, unique=True)
            summary = sa.Column(sa.Unicode(255), nullable=False)
            article = relationship(Article, backref=backref("details", uselist=False))

        self.Article = Article
        self.ArticleDetails = ArticleDetails

    def test_revert_scalar_association_proxy(self, session: Session):
        article = self.Article(name="article1")
        article.details = self.ArticleDetails(summary="original")
        session.add(article)
        session.commit()

        article.details.summary = "updated"
        session.commit()

        article.versions[0].revert(relations=["summary"])
        session.commit()

        assert article.summary == "original"


class TestObjectAssociationProxyRevert(TestCase):
    def create_models(self, decl_base, versioning_options):
        class User(decl_base):
            __tablename__ = "user"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            keywords = association_proxy(
                "keyword_links",
                "keyword",
                creator=lambda keyword: UserKeyword(keyword=keyword),
            )

        class Keyword(decl_base):
            __tablename__ = "keyword"
            __versioned__ = {}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)

        class UserKeyword(decl_base):
            __tablename__ = "user_keyword"
            __versioned__ = {}

            user_id = sa.Column(sa.Integer, sa.ForeignKey(User.id), primary_key=True)
            keyword_id = sa.Column(sa.Integer, sa.ForeignKey(Keyword.id), primary_key=True)
            user = relationship(User, backref=backref("keyword_links", cascade="all, delete-orphan"))
            keyword = relationship(Keyword)

        self.User = User
        self.Keyword = Keyword
        self.UserKeyword = UserKeyword

    def test_revert_object_association_proxy(self, session: Session):
        keyword1 = self.Keyword(name="keyword1")
        user = self.User(name="user1", keywords=[keyword1])
        session.add(user)
        session.commit()

        user.name = "updated"
        user.keywords.append(self.Keyword(name="keyword2"))
        session.commit()

        user.versions[0].revert(relations=["keywords"])
        session.commit()

        assert user.name == "user1"
        assert user.keywords == [keyword1]
