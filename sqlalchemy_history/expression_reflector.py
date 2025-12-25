"""This is ExpressionReflector used for generating expression queries."""

from __future__ import annotations

import typing as t

import sqlalchemy as sa
from sqlalchemy.sql.expression import bindparam

from sqlalchemy_history.exc import TableNotVersioned
from sqlalchemy_history.utils import version_table


if t.TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase, RelationshipProperty
    from sqlalchemy.sql.visitors import ExternallyTraversible

_T = t.TypeVar("_T", bound="DeclarativeBase")


class VersionExpressionReflector(sa.sql.visitors.ReplacingCloningVisitor):
    def __init__(self, parent: _T, relationship: RelationshipProperty) -> None:
        self.parent = parent
        self.relationship = relationship

    def replace(self, elem: ExternallyTraversible) -> ExternallyTraversible | None:
        if not isinstance(elem, sa.Column):
            return None
        try:
            table = version_table(elem.table)
        except TableNotVersioned:
            reflected_column = elem
        else:
            reflected_column = table.c[elem.name]
            if elem in self.relationship.local_columns and table == self.parent.__table__:
                reflected_column = bindparam(elem.key, getattr(self.parent, elem.key))

        return reflected_column

    def __call__(self, expr: ExternallyTraversible | None) -> ExternallyTraversible | None:
        return self.traverse(expr)
