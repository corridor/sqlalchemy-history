import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase


class TestCommonBaseClass(TestCase):
    def create_models(self, decl_base, versioning_options):
        class Versioned:
            __versioned__ = {"base_classes": (decl_base,)}

        class TextItem(decl_base, Versioned):
            __tablename__ = "text_item"

            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )

        class Article(decl_base, Versioned):
            __tablename__ = "article"
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq", start=1), autoincrement=True, primary_key=True
            )

        self.TextItem = TextItem
        self.Article = Article

    def test_each_class_has_distinct_translation_class(self):
        class_ = version_class(self.TextItem)
        assert class_.__name__ == "TextItemVersion"
        class_ = version_class(self.Article)
        assert class_.__name__ == "ArticleVersion"
