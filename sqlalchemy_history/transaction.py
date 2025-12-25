"""Transaction model makes transactions for history tables"""

from __future__ import annotations

import datetime
import typing as t
from collections import OrderedDict

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import object_session, relationship

from sqlalchemy_history._typing import SupportsVersioning
from sqlalchemy_history.exc import ImproperlyConfigured, NoChangesAttribute
from sqlalchemy_history.factory import ModelFactory


if t.TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.sql.compiler import SQLCompiler

    from sqlalchemy_history.manager import VersioningManager


@compiles(sa.types.BigInteger, "sqlite")
def compile_big_integer(element: sa.types.BigInteger, compiler: SQLCompiler, **kw) -> str:
    return "INTEGER"


class TransactionBase(SupportsVersioning):
    issued_at = sa.Column(sa.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    @property
    def entity_names(self) -> list[str]:
        """Return a list of entity names that changed during this transaction.

        Raises a NoChangesAttribute exception if the 'changes' column does
        not exist, most likely because TransactionChangesPlugin is not enabled.
        """
        if hasattr(self, "changes"):
            return [changes.entity_name for changes in self.changes]
        raise NoChangesAttribute

    @property
    def changed_entities(self) -> dict[type[DeclarativeBase], t.Sequence[t.Any]]:
        """Return all changed entities for this transaction log entry.

        Entities are returned as a dict where keys are entity classes and
        values lists of entitites that changed in this transaction.
        """
        manager = self.__versioning_manager__
        tuples = set(manager.version_class_map.items())
        entities = {}

        session = object_session(self)

        for class_, version_class in tuples:
            try:
                if class_.__name__ not in self.entity_names:
                    continue
            except NoChangesAttribute:
                pass

            tx_column = manager.option(class_, "transaction_column_name")

            entities[version_class] = (
                session.query(version_class).filter(getattr(version_class, tx_column) == self.id)
            ).all()
        return entities


class TransactionFactory(ModelFactory):
    model_name = "Transaction"

    def __init__(self, *, remote_addr: bool = True) -> None:
        self.remote_addr = remote_addr

    def create_class(self, manager: VersioningManager) -> type[TransactionBase]:
        """Create Transaction class."""

        class Transaction(manager.declarative_base, TransactionBase):
            __tablename__ = "transaction"
            __versioning_manager__ = manager

            id = sa.Column(
                sa.types.BigInteger,
                sa.schema.Sequence("transaction_id_seq", start=1, order=True),
                primary_key=True,
                autoincrement=True,
            )

            if self.remote_addr:
                remote_addr = sa.Column(sa.String(50))

            if manager.user_cls:
                user_cls = manager.user_cls
                Base = manager.declarative_base
                registry = Base.registry._class_registry

                if isinstance(user_cls, str):
                    try:
                        user_cls = registry[user_cls]
                    except KeyError as err:
                        raise ImproperlyConfigured(
                            "Could not build relationship between Transaction"
                            f" and {user_cls}. {user_cls} was not found in declarative class "
                            "registry. Either configure VersioningManager to "
                            "use different user class or disable this "
                            "relationship ",
                        ) from err

                user_id = sa.Column(
                    sa.inspect(user_cls).primary_key[0].type,
                    sa.ForeignKey(sa.inspect(user_cls).primary_key[0]),
                    index=True,
                )

                user = relationship(user_cls)

            def __repr__(self) -> str:
                fields = ["id", "issued_at", "user"]
                field_values = OrderedDict(
                    (field, getattr(self, field)) for field in fields if hasattr(self, field)
                )
                return "<Transaction {}>".format(
                    ", ".join(f"{field}={value!r}" for field, value in field_values.items())
                )

        return Transaction
