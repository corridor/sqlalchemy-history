from sqlalchemy_history import tx_column_name, version_class
from sqlalchemy_history.utils import end_tx_attr
from tests import TestCase, create_test_cases


setting_variants = {
    "transaction_column_name": ["transaction_id", "tx_id"],
}


class TxColumnNameTestCase(TestCase):
    def test_with_version_class(self, versioning_options):
        assert tx_column_name(version_class(self.Article)) == versioning_options["transaction_column_name"]

    def test_with_version_obj(self, versioning_options):
        history_obj = version_class(self.Article)()
        assert tx_column_name(history_obj) == versioning_options["transaction_column_name"]

    def test_with_versioned_class(self, versioning_options):
        assert tx_column_name(self.Article) == versioning_options["transaction_column_name"]


create_test_cases(TxColumnNameTestCase, setting_variants=setting_variants)


setting_variants = {
    "versioning_strategy": ["validity"],
}


class TxColumnNameTestCaseWithValidity(TestCase):
    def test_end_tx_attr(self, session, versioning_options):
        article = self.Article(name="tc1")
        session.add(article)
        session.commit()
        assert end_tx_attr(article.versions[0]).name == versioning_options["end_transaction_column_name"]


create_test_cases(TxColumnNameTestCaseWithValidity, setting_variants=setting_variants)
