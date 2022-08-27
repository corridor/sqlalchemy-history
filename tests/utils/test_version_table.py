from tests import TestCase, uses_native_versioning

from sqlalchemy_continuum.utils import version_table

class TestVersionTableDefault(TestCase):

    def test_version_table(self):
        ArticleVersionTableName = version_table(self.Article.__table__)
        assert ArticleVersionTableName.fullname == 'article_version'

class TestVersionTableUserDefined(TestCase):

    @property
    def options(self):
        return {
            'create_models': self.should_create_models,
            'native_versioning': uses_native_versioning(),
            'base_classes': (self.Model, ),
            'strategy': self.versioning_strategy,
            'transaction_column_name': self.transaction_column_name,
            'end_transaction_column_name': self.end_transaction_column_name,
            'table_name': '%s_user_defined'
        }

    def test_version_table(self):
        ArticleVersionTableName = version_table(self.Article.__table__)
        assert ArticleVersionTableName.fullname == 'article_user_defined'
