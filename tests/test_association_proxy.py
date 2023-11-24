import sqlalchemy as sa
from sqlalchemy_history.utils import get_association_proxies, version_class

from tests import TestCase


class TestAssociationProxy(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

            upanaam = sa.ext.associationproxy.association_proxy("tags", "name")

        class Tag(self.Model):
            __tablename__ = "tag"
            __versioned__ = {}

            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = sa.orm.relationship(Article, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def test_association_proxy_mapping(self):
        assoc_mapping = get_association_proxies(self.Article)
        assert len(assoc_mapping) == 1
        assert list(assoc_mapping.keys())[0] == "upanaam"
        assert isinstance(assoc_mapping["upanaam"], sa.ext.associationproxy.AssociationProxy)

    def test_association_proxy_detection(self):
        """
        Currently Versioned Model have a proxy mapped as a property due limitation in the way relationships
         are handled, For now a property in versioned model should be available for proxy attributes of
         orginal model
        """
        assert issubclass(type(self.Article.upanaam), sa.ext.associationproxy.AssociationProxyInstance)
        assert isinstance(version_class(self.Article).upanaam, property)

    def test_association_proxy_retrieval(self):
        tag = self.Tag(name="tag1")
        self.session.add(tag)
        article = self.Article(name="article1", tags=[tag])
        self.session.add(article)
        self.session.commit()
        tag2 = self.Tag(name="tag2")
        self.session.add(tag2)
        article.tags += [tag2]
        article.name = "updated"
        self.session.add(article)
        self.session.commit()
        assert article.versions.count() == 2
        assert len(article.versions.all()[0].tags) == 1
        assert len(article.versions.all()[1].tags) == 2
        assert set(article.versions.all()[0].upanaam) == {"tag1"}
        assert set(article.versions.all()[1].upanaam) == {"tag1", "tag2"}
