from sqlalchemy_history.utils import version_class
from tests import TestCase


class TestVersionModelBuilder(TestCase):
    def test_builds_relationship(self):
        assert self.Article.versions

    def test_parent_has_access_to_versioning_manager(self):
        assert self.Article.__versioning_manager__


class TestVersionModelBuilderWithCustomName(TestCase):
    @property
    def options(self):
        return {
            "create_models": self.should_create_models,
            "base_classes": (self.Model,),
            "strategy": self.versioning_strategy,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
            "table_name": "%s_user_defined",
        }

    def test_versioned_class_name(self):
        assert version_class(self.Article).__name__ == f"{self.Article.__name__}UserDefined"
