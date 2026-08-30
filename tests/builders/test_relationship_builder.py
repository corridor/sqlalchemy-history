import sqlalchemy as sa
from sqlalchemy.orm import relationship

from tests import TestCase


class TestRelationshipBuilderWithNonVersionedModel(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Article(decl_base):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (decl_base,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)

        class Tag(decl_base):
            __tablename__ = "tag"
            __versioned__ = {"versioning": False, "base_classes": (decl_base,)}

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )
            name = sa.Column(sa.Unicode(255))
            article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
            article = relationship(Article, backref="tags")

        self.Article = Article
        self.Tag = Tag

    def test_does_not_build_relations_to_non_versioned_classes(self):
        pass
