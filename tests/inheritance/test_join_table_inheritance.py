import pytest
import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase, create_test_cases


class JoinTableInheritanceTestCase(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {"base_classes": (self.Model,)}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )

            name = sa.Column(sa.Unicode(255))

            discriminator = sa.Column(sa.Unicode(100))

            __mapper_args__ = {"polymorphic_on": discriminator, "with_polymorphic": "*"}

        class Article(TextItem):
            __tablename__ = "article"
            __mapper_args__ = {"polymorphic_identity": "article"}
            id = sa.Column(sa.Integer, sa.ForeignKey(TextItem.id), primary_key=True)

        class BlogPost(TextItem):
            __tablename__ = "blog_post"
            __mapper_args__ = {"polymorphic_identity": "blog_post"}
            id = sa.Column(sa.Integer, sa.ForeignKey(TextItem.id), primary_key=True)

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    @pytest.fixture(autouse=True)
    def setup_method_for_join_inheritance(self, session):
        self.TextItemVersion = version_class(self.TextItem)
        self.ArticleVersion = version_class(self.Article)
        self.BlogPostVersion = version_class(self.BlogPost)
        yield
        del self.TextItemVersion, self.ArticleVersion, self.BlogPostVersion

    def test_each_class_has_distinct_version_table(self):
        assert self.TextItemVersion.__table__.name == "text_item_version"
        assert self.ArticleVersion.__table__.name == "article_version"
        assert self.BlogPostVersion.__table__.name == "blog_post_version"

        assert issubclass(self.ArticleVersion, self.TextItemVersion)
        assert issubclass(self.BlogPostVersion, self.TextItemVersion)

    def test_each_object_has_distinct_version_class(self, session):
        article = self.Article()
        blogpost = self.BlogPost()
        textitem = self.TextItem()

        session.add(article)
        session.add(blogpost)
        session.add(textitem)
        session.commit()

        # assert type(textitem.versions[0]) is self.TextItemVersion
        assert type(article.versions[0]) is self.ArticleVersion
        assert type(blogpost.versions[0]) is self.BlogPostVersion

    def test_all_tables_contain_transaction_id_column(self):
        tx_column = self.options["transaction_column_name"]

        assert tx_column in self.TextItemVersion.__table__.c
        assert tx_column in self.ArticleVersion.__table__.c
        assert tx_column in self.BlogPostVersion.__table__.c

    def test_with_polymorphic(self, session):
        article = self.Article()
        session.add(article)
        session.commit()

        version_obj = session.scalars(sa.select(self.TextItemVersion)).first()
        assert isinstance(version_obj, self.ArticleVersion)

    def test_consecutive_insert_and_delete(self, session):
        article = self.Article()
        session.add(article)
        session.flush()
        session.delete(article)
        session.commit()

    def test_assign_transaction_id_to_both_parent_and_child_tables(self, session):
        tx_column = self.options["transaction_column_name"]
        article = self.Article()
        session.add(article)
        session.commit()
        assert session.execute(sa.text(f"SELECT {tx_column} FROM article_version")).fetchone()[0]
        assert session.execute(sa.text(f"SELECT {tx_column} FROM text_item_version")).fetchone()[0]

    def test_primary_keys(self):
        tx_column = self.options["transaction_column_name"]
        table = self.TextItemVersion.__table__
        assert len(table.primary_key.columns)
        assert "id" in table.primary_key.columns
        assert tx_column in table.primary_key.columns
        table = self.ArticleVersion.__table__
        assert len(table.primary_key.columns)
        assert "id" in table.primary_key.columns
        assert tx_column in table.primary_key.columns

    def test_updates_end_transaction_id_to_all_tables(self, session):
        if self.options["strategy"] == "subquery":
            pytest.skip(reason="Skip end_tx_id test if not using validity strategy")

        end_tx_column = self.options["end_transaction_column_name"]
        tx_column = self.options["transaction_column_name"]
        article = self.Article()
        session.add(article)
        session.commit()
        article.name = "Updated article"
        session.commit()
        assert article.versions.count() == 2

        assert session.execute(
            sa.text(f"SELECT {end_tx_column} FROM text_item_version ORDER BY {tx_column}")
        ).fetchone()[0]
        assert session.execute(sa.text(f"SELECT {end_tx_column} FROM article_version ORDER BY {tx_column}")).fetchone()[
            0
        ]


create_test_cases(JoinTableInheritanceTestCase)


class TestDeepJoinedTableInheritance(TestCase):
    def create_models(self):
        class Node(self.Model):
            __versioned__ = {}
            __tablename__ = "node"
            __mapper_args__ = {
                "polymorphic_on": "type",
                "polymorphic_identity": "node",
                "with_polymorphic": "*",
            }

            id = sa.Column(sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), primary_key=True)
            type = sa.Column(sa.String(30), nullable=False)

        class Content(Node):
            __versioned__ = {}
            __tablename__ = "content"
            __mapper_args__ = {"polymorphic_identity": "content"}
            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                sa.ForeignKey("node.id"),
                primary_key=True,
            )
            description = sa.Column(sa.UnicodeText())

        class Document(Content):
            __versioned__ = {}
            __tablename__ = "document"
            __mapper_args__ = {"polymorphic_identity": "document"}
            id = sa.Column(
                sa.Integer,
                sa.Sequence(f"{__tablename__}_seq", start=1),
                sa.ForeignKey("content.id"),
                primary_key=True,
            )
            body = sa.Column(sa.UnicodeText)

        self.Node = Node
        self.Content = Content
        self.Document = Document

    def test_insert(self, session):
        document = self.Document()
        session.add(document)
        session.commit()
        assert session.execute(sa.text("SELECT COUNT(1) FROM document_version")).scalar() == 1
        assert session.execute(sa.text("SELECT COUNT(1) FROM content_version")).scalar() == 1
        assert session.execute(sa.text("SELECT COUNT(1) FROM node_version")).scalar() == 1
