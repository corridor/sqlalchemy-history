import typing as t

from sqlalchemy.orm import ColumnProperty

from sqlalchemy_history.operation import Operation
from sqlalchemy_history.plugins.base import Plugin
from sqlalchemy_history.utils import is_internal_column, versioned_column_properties


if t.TYPE_CHECKING:
    from sqlalchemy_history.unit_of_work import UnitOfWork


class NullDeletePlugin(Plugin):
    def should_nullify_column(self, version_obj, prop: ColumnProperty) -> bool:
        """Return whether or not given column of given version object should
        be nullified (set to None) at the end of the transaction.

        :param version_obj: Version object to check the attribute nullification
        :parem prop:        SQLAlchemy ColumnProperty object
        """
        return (
            version_obj.operation_type == Operation.DELETE
            and not prop.columns[0].primary_key
            and not is_internal_column(version_obj, prop.key)
        )

    def after_create_version_object(self, uow: "UnitOfWork", parent_obj, version_obj) -> None:
        for prop in versioned_column_properties(parent_obj):
            if self.should_nullify_column(version_obj, prop):
                setattr(version_obj, prop.key, None)
