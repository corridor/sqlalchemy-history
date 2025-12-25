from __future__ import annotations

import typing as t

import typing_extensions as te


if t.TYPE_CHECKING:
    from sqlalchemy_history.manager import VersioningManager


class VersioningOptions(te.TypedDict):
    versioning: bool
    base_classes: t.Any
    table_name: str
    exclude: t.Sequence[t.Any]
    include: t.Sequence[t.Any]
    create_models: bool
    create_tables: bool
    transaction_column_name: str
    end_transaction_column_name: str
    operation_type_column_name: str
    strategy: t.Literal["validity", "subquery"]
    use_module_name: str


class SupportsVersioning(t.Protocol):
    __versioned__: t.ClassVar[VersioningOptions]
    __versioning_manager__: VersioningManager
