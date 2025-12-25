from __future__ import annotations

from sqlalchemy_history import tx_column_name, version_class
from sqlalchemy_history.utils import end_tx_attr
from tests import TestCase, create_test_cases


setting_variants = {
    "transaction_column_name": ["transaction_id", "tx_id"],
}


class TxColumnNameTestCase(TestCase):
    def test_with_version_class(self):
        assert tx_column_name(version_class(self.Article)) == self.options["transaction_column_name"]

    def test_with_version_obj(self):
        history_obj = version_class(self.Article)()
        assert tx_column_name(history_obj) == self.options["transaction_column_name"]

    def test_with_versioned_class(self):
        assert tx_column_name(self.Article) == self.options["transaction_column_name"]


create_test_cases(TxColumnNameTestCase, setting_variants=setting_variants)


setting_variants = {
    "versioning_strategy": ["validity"],
}


class TxColumnNameTestCaseWithValidity(TestCase):
    def test_end_tx_attr(self):
        article = self.Article(name="tc1")
        self.session.add(article)
        self.session.commit()
        assert end_tx_attr(article.versions[0]).name == self.options["end_transaction_column_name"]


create_test_cases(TxColumnNameTestCaseWithValidity, setting_variants=setting_variants)
