"""This is ExpressionReflector used for generating expression queries."""

import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.sql.visitors import ExternallyTraversible, ReplacingCloningVisitor

from sqlalchemy_history.exc import TableNotVersioned
from sqlalchemy_history.utils import version_table


class VersionExpressionReflector(ReplacingCloningVisitor):
    def __init__(self, parent, relationship: RelationshipProperty) -> None:
        self.parent = parent
        self.relationship = relationship

    def replace(self, elem: ExternallyTraversible) -> t.Optional[ExternallyTraversible]:
        if not isinstance(elem, sa.Column):
            return None
        try:
            table = version_table(elem.table)
        except TableNotVersioned:
            reflected_column = elem
        else:
            if table is None:
                raise AssertionError(f"Unable to find version_table for {elem.table}")
            reflected_column = table.c[elem.name]
            if elem in self.relationship.local_columns and table == self.parent.__table__:
                reflected_column = bindparam(elem.key, getattr(self.parent, elem.key))

        return reflected_column

    def __call__(self, expr: ExternallyTraversible) -> ExternallyTraversible:
        return self.traverse(expr)
