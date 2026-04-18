"""
TransactionChanges provides way of keeping track efficiently which declarative
models were changed in given transaction. This can be useful when transactions
need to be queried afterwards for problems such as:

1. Find all transactions which affected `User` model.

2. Find all transactions which didn't affect models `Entity` and `Event`.

The plugin works in two ways. On class instrumentation phase this plugin
creates a special transaction model called `TransactionChanges`. This model is
associated with table called `transaction_changes`, which has only only two
fields: transaction_id and entity_name. If for example transaction consisted
of saving 5 new User entities and 1 Article entity, two new rows would be
inserted into transaction_changes table.

================    =================
transaction_id          entity_name
----------------    -----------------
233678                  User
233678                  Article
================    =================
"""

import typing as t

import sqlalchemy as sa
import sqlalchemy.orm

from sqlalchemy_history.factory import ModelFactory
from sqlalchemy_history.plugins.base import Plugin


if t.TYPE_CHECKING:
    from sqlalchemy_history.manager import VersioningManager
    from sqlalchemy_history.unit_of_work import UnitOfWork


class TransactionChangesBase:
    transaction_id: sa.orm.Mapped[int] = sa.orm.mapped_column(sa.BigInteger, primary_key=True)
    entity_name: sa.orm.Mapped[str] = sa.orm.mapped_column(sa.Unicode(255), primary_key=True)


class TransactionChangesFactory(ModelFactory):
    model_name = "TransactionChanges"

    def create_class(self, manager: "VersioningManager") -> type[t.Any]:
        """Create TransactionChanges class.

        :param manager:

        """

        class TransactionChanges(manager.declarative_base, TransactionChangesBase):
            __tablename__ = "transaction_changes"

        TransactionChanges.transaction = sa.orm.relationship(
            manager.transaction_cls,
            backref=sa.orm.backref(
                "changes",
            ),
            primaryjoin=(f"{manager.transaction_cls.__name__}.id == TransactionChanges.transaction_id"),
            foreign_keys=[TransactionChanges.transaction_id],
        )
        return TransactionChanges


class TransactionChangesPlugin(Plugin):
    objects = None

    def after_build_tx_class(self, manager: "VersioningManager") -> None:
        self.model_class = TransactionChangesFactory()(manager)

    def after_build_models(self, manager: "VersioningManager") -> None:
        self.model_class = TransactionChangesFactory()(manager)

    def before_create_version_objects(self, uow: "UnitOfWork", session: sa.orm.Session) -> None:
        for entity in uow.operations.entities:
            params = uow.current_transaction.id, str(entity.__name__)
            changes = session.get(self.model_class, params)
            if not changes:
                changes = self.model_class(
                    transaction_id=uow.current_transaction.id,
                    entity_name=str(entity.__name__),
                )
                session.add(changes)

    def clear(self) -> None:
        self.objects = None

    def after_rollback(self, uow: "UnitOfWork", session: sa.orm.Session) -> None:
        self.clear()

    def ater_commit(self, uow: "UnitOfWork", session: sa.orm.Session) -> None:
        self.clear()

    def after_version_class_built(self, parent_cls: type[t.Any], version_cls: type[t.Any]) -> None:
        parent_cls.__versioned__["transaction_changes"] = self.model_class
