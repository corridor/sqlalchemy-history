from tests import TestCase


class TestVersionModelBuilder(TestCase):
    def test_builds_relationship(self):
        assert self.Article.versions

    def test_parent_has_access_to_versioning_manager(self):
        assert self.Article.__versioning_manager__

class TestGenericReprModelBuilder(TestCase):

    @property
    def options(self):
        return {
            "create_models": self.should_create_models,
            "base_classes": None,
            "strategy": self.versioning_strategy,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    def test_version_cls_repr(self):
        # If no base classes specified only then generic_repr should be set
        article = self.Article(name="testing")
        self.session.add(article)
        self.session.commit()
        assert repr(article.versions[0]) == "ArticleVersion(id=1, transaction_id=1, operation_type=0)"

class TestNoGenericReprModelBuilder(TestCase):

    @property
    def options(self):
        class ReprMixin:
            def __repr__(self):
                return f"Class_{self.__class__.__name__}(id={self.id})"

        return {
            "create_models": self.should_create_models,
            "base_classes": (self.Model,ReprMixin),
            "strategy": self.versioning_strategy,
            "transaction_column_name": self.transaction_column_name,
            "end_transaction_column_name": self.end_transaction_column_name,
        }

    def test_version_cls_repr(self):
        # If no base classes specified only then generic_repr should be set
        article = self.Article(name="testing")
        self.session.add(article)
        self.session.commit()
        assert repr(article.versions[0]) == "Class_ArticleVersion(id=1)"
