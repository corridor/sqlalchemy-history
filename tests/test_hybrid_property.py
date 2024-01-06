import datetime
import sqlalchemy as sa
from sqlalchemy_history.utils import version_class

from tests import TestCase


class TestHybridProperty(TestCase):
    def create_models(self):
        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {}

            id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)
            description = sa.Column(sa.UnicodeText)
            publish = sa.Column(sa.DateTime, default=datetime.datetime.now(datetime.timezone.utc))

            @sa.ext.hybrid.hybrid_property
            def time_from_publish(self):
                return datetime.datetime.today() - self.publish

        self.Article = Article

    def test_hybrid_property_mapping_for_versioned_class(self):
        version_class(self.Article).time_from_publish
