from sqlalchemy_continuum import versioning_manager
from tests import TestCase


class TestMemoryClearing(TestCase):
    def test_something(self):
        article = self.Article()
        article.name = u'Some article'
        article.content = u'Some content'
        self.session.add(article)
        self.session.commit()
        assert versioning_manager.units_of_work == {}
