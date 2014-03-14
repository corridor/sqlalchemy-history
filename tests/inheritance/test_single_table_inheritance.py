from pytest import mark
import sqlalchemy as sa
from sqlalchemy_continuum import versioning_manager, version_class
from tests import TestCase


class TestSingleTableInheritance(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = 'text_item'
            __versioned__ = {
                'base_classes': (self.Model, )
            }
            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

            discriminator = sa.Column(
                sa.Unicode(100)
            )

            __mapper_args__ = {
                'polymorphic_on': discriminator,
            }

        class Article(TextItem):
            __mapper_args__ = {'polymorphic_identity': u'article'}
            name = sa.Column(sa.Unicode(255))

        class BlogPost(TextItem):
            __mapper_args__ = {'polymorphic_identity': u'blog_post'}
            title = sa.Column(sa.Unicode(255))

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.TextItemVersion = version_class(self.TextItem)
        self.ArticleVersion = version_class(self.Article)
        self.BlogPostVersion = version_class(self.BlogPost)

    def test_version_class_map(self):
        manager = self.TextItem.__versioning_manager__
        assert len(manager.version_class_map.keys()) == 3

    def test_transaction_relations(self):
        tx_log = versioning_manager.transaction_cls
        assert tx_log.text_items
        assert tx_log.articles
        assert tx_log.blog_posts

    def test_each_class_has_distinct_version_class(self):
        assert self.TextItemVersion.__table__.name == 'text_item_version'
        assert self.ArticleVersion.__table__.name == 'text_item_version'
        assert self.BlogPostVersion.__table__.name == 'text_item_version'
        assert issubclass(self.ArticleVersion, self.TextItemVersion)
        assert issubclass(self.BlogPostVersion, self.TextItemVersion)

    @mark.skipif('True')
    def test_each_object_has_distinct_version_class(self):
        article = self.Article()
        blogpost = self.BlogPost()
        textitem = self.TextItem()

        self.session.add(article)
        self.session.add(blogpost)
        self.session.add(textitem)
        self.session.commit()

        assert type(textitem.versions[0]) == self.TextItemVersion
        assert type(article.versions[0]) == self.ArticleVersion
        assert type(blogpost.versions[0]) == self.BlogPostVersion

    def test_transaction_changed_entities(self):
        article = self.Article()
        article.name = u'Text 1'
        self.session.add(article)
        self.session.commit()
        Transaction = versioning_manager.transaction_cls
        transaction = (
            self.session.query(Transaction)
            .order_by(sa.sql.expression.desc(Transaction.issued_at))
        ).first()
        assert transaction.entity_names == [u'Article']
        assert transaction.changed_entities