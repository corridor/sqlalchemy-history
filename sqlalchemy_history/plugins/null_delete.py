import typing as t

import sqlalchemy as sa

from sqlalchemy_history.operation import Operation
from sqlalchemy_history.plugins.base import Plugin
from sqlalchemy_history.utils import is_internal_column, versioned_column_properties


class NullDeletePlugin(Plugin):
    def should_nullify_column(
        self,
        version_obj: t.Any,
        prop: sa.orm.ColumnProperty[t.Any],
    ) -> bool:
        """Return whether or not given column of given version object should
        be nullified (set to None) at the end of the transaction.

        :param version_obj: Version object to check the attribute nullification
        :paremt prop:
            SQLAlchemy ColumnProperty object
        """
        return (
            version_obj.operation_type == Operation.DELETE
            and not prop.columns[0].primary_key
            and not is_internal_column(version_obj, prop.key)
        )

    def after_create_version_object(self, uow: t.Any, parent_obj: t.Any, version_obj: t.Any) -> None:
        for prop in versioned_column_properties(parent_obj):
            if self.should_nullify_column(version_obj, prop):
                setattr(version_obj, prop.key, None)
