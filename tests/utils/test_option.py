import pytest
import sqlalchemy as sa

from sqlalchemy_history.utils import option
from tests import TestCase


class TestOption(TestCase):
    @pytest.mark.parametrize(
        "attribute",
        [
            "versioning",
            "base_classes",
            "table_name",
            "exclude",
            "include",
            "create_models",
            "create_tables",
            "transaction_column_name",
            "end_transaction_column_name",
            "operation_type_column_name",
            "strategy",
            "use_module_name",
        ],
    )
    def test_option(self, attribute):
        assert option(self.Article, attribute) == option(sa.orm.aliased(self.Article), attribute)
