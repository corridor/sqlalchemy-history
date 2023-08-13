import pytest
import sqlalchemy as sa
from sqlalchemy_history import versioning_manager, version_class
from tests import TestCase, create_test_cases


class SingleTableInheritanceTestCase(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {"base_classes": (self.Model,)}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            discriminator = sa.Column(sa.Unicode(100))

            __mapper_args__ = {
                "polymorphic_on": discriminator,
                "polymorphic_identity": "base",
                "with_polymorphic": "*",
            }

        class Article(TextItem):
            __mapper_args__ = {"polymorphic_identity": "article"}
            name = sa.Column(sa.Unicode(255))

            @sa.ext.declarative.declared_attr
            def status(cls):
                return sa.Column("_status", sa.Unicode(255))

        class BlogPost(TextItem):
            __mapper_args__ = {"polymorphic_identity": "blog_post"}
            title = sa.Column(sa.Unicode(255))

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    @pytest.fixture(autouse=True)
    def setup_method_for_single_inheritance_objects(self):
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
        assert self.ArticleVersion.__table__.name == "text_item_version"
        assert self.BlogPostVersion.__table__.name == "text_item_version"

    def test_each_object_has_distinct_version_class(self):
        article = self.Article()
        blogpost = self.BlogPost()
        textitem = self.TextItem()

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

    def test_declared_attr_inheritance(self):
        assert self.ArticleVersion.status


create_test_cases(SingleTableInheritanceTestCase)
