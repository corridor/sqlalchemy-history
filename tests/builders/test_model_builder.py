from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import MappedColumn

from sqlalchemy_history.model_builder import copy_mapper_args
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
            "base_classes": (self.Model, ReprMixin),
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


class TestCopyMapperArgs(TestCase):
    def test_copy_mapper_args_with_mapped_column_polymorphic_on(self):
        # Test that copy_mapper_args handles MappedColumn for polymorphic_on

        class MockModel:
            __mapper_args__ = {"polymorphic_on": MappedColumn(sa.String(50), name="type")}

        args = copy_mapper_args(MockModel)
        assert args["polymorphic_on"] == "type"

    def test_copy_mapper_args_with_str_polymorphic_on(self):
        # Test that copy_mapper_args handles str for polymorphic_on

        class MockModel:
            __mapper_args__ = {"polymorphic_on": "type"}

        args = copy_mapper_args(MockModel)
        assert args["polymorphic_on"] == "type"

    def test_copy_mapper_args_with_column_polymorphic_on(self):
        # Test that copy_mapper_args handles Column for polymorphic_on

        column = sa.Column(sa.String(50), name="type")

        class MockModel:
            __mapper_args__ = {"polymorphic_on": column}

        args = copy_mapper_args(MockModel)
        assert args["polymorphic_on"] == "type"
