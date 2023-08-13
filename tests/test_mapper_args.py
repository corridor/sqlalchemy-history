import pytest
import sqlalchemy as sa

from sqlalchemy_history import version_class
from tests import TestCase


class TestColumnPrefix(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {"base_classes": (self.Model,)}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            name = sa.Column(sa.Unicode(255))

            __mapper_args__ = {"column_prefix": "_"}

        self.TextItem = TextItem

    @pytest.fixture(autouse=True)
    def setup_method_for_col_prefix(self):
        self.TextItemVersion = version_class(self.TextItem)
        yield
        del self.TextItemVersion

    def test_supports_column_prefix(self):
        assert self.TextItemVersion._id
        assert self.TextItem._id
