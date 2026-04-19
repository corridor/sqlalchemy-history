import typing as t

import sqlalchemy as sa
from sqlalchemy.orm import Mapper


class _MappedInstance(t.Protocol):
    __table__: sa.Table
    __mapper__: Mapper[t.Any]


_O = t.TypeVar("_O", bound=_MappedInstance)
"""The 'ORM mapped object' type."""
