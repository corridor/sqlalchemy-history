import sqlalchemy as sa
from pytest import mark, fixture

from sqlalchemy_history import version_class, versioning_manager
from tests import TestCase


class TestConreteTableInheritance(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {"base_classes": (self.Model,)}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            discriminator = sa.Column(sa.Unicode(100))

            __mapper_args__ = {"polymorphic_on": discriminator}

        class Article(TextItem):
            __tablename__ = "article"
            __mapper_args__ = {"polymorphic_identity": "article", "concrete": True}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))

        class BlogPost(TextItem):
            __tablename__ = "blog_post"
            __mapper_args__ = {"polymorphic_identity": "blog_post", "concrete": True}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )
            title = sa.Column(sa.Unicode(255))

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    @fixture(autouse=True)
    def setup_method_for_concerete_inheritance(self, setup_session):
        self.TextItemVersion = version_class(self.TextItem)
        self.ArticleVersion = version_class(self.Article)
        self.BlogPostVersion = version_class(self.BlogPost)
        yield
        del self.TextItemVersion, self.ArticleVersion, self.BlogPostVersion

    def test_inheritance(self):
        assert issubclass(self.ArticleVersion, self.TextItemVersion)
        assert issubclass(self.BlogPostVersion, self.TextItemVersion)

    def test_version_class_map(self):
        manager = self.TextItem.__versioning_manager__
        assert len(manager.version_class_map.keys()) == 3

    def test_each_class_has_distinct_version_class(self):
        assert self.TextItemVersion.__table__.name == "text_item_version"
        assert self.ArticleVersion.__table__.name == "article_version"
        assert self.BlogPostVersion.__table__.name == "blog_post_version"

    @mark.skipif("True", reason="concrete property is not supported yet")
    def test_each_object_has_distinct_version_class(self):  # pragma: no cover
        article = self.Article(name="a")
        blogpost = self.BlogPost(title="b")
        textitem = self.TextItem(discriminator="blog_post")

        self.session.add(article)
        self.session.add(blogpost)
        self.session.add(textitem)
        self.session.commit()

        assert type(textitem.versions[0]) is self.TextItemVersion
        assert type(article.versions[0]) is self.ArticleVersion
        assert type(blogpost.versions[0]) is self.BlogPostVersion

    def test_transaction_changed_entities(self):
        article = self.Article()
        article.name = "Text 1"
        self.session.add(article)
        self.session.commit()
        Transaction = versioning_manager.transaction_cls
        transaction = (
            self.session.query(Transaction).order_by(sa.sql.expression.desc(Transaction.issued_at))
        ).first()
        assert transaction.entity_names == ["Article"]
        assert transaction.changed_entities
