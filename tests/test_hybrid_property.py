import datetime
import pytest
import sqlalchemy as sa
from sqlalchemy_history.utils import get_hybrid_property_mapping, version_class

from tests import TestCase


class TestAssociationProxy(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            publish = sa.Column(sa.DateTime, default=sa.func.utcnow)

            @sa.ext.hybrid.hybrid_property
            def time_from_publish(self):
                return datetime.date.today() - self.publish

        self.Article = Article

    def test_hybrid_property_mapping(self):
        hybrid_property_mapping = get_hybrid_property_mapping(self.Article)
        assert len(hybrid_property_mapping) == 1
        assert list(hybrid_property_mapping.keys())[0] == "time_from_publish"
        assert isinstance(hybrid_property_mapping["time_from_publish"], sa.ext.hybrid.hybrid_property)

    def test_hybrid_property_mapping_for_versioned_class(self):
        try:
            version_class(self.Article).time_from_publish
        except AttributeError as atr:
            raise atr
