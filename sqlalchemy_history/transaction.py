"""Transaction model makes transactions for history tables
"""

from datetime import datetime
from functools import partial

from collections import OrderedDict
import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_utils.functions import get_primary_keys

from sqlalchemy_history.exc import ImproperlyConfigured
from sqlalchemy_history.factory import ModelFactory
from sqlalchemy_history.operation import Operation


@compiles(sa.types.BigInteger, "sqlite")
def compile_big_integer(element, compiler, **kw):
    return "INTEGER"


class NoChangesAttribute(Exception):
    pass


class TransactionBase(object):
    issued_at = sa.Column(sa.DateTime, default=datetime.utcnow)

    @property
    def entity_names(self):
        """Return a list of entity names that changed during this transaction.

        Raises a NoChangesAttribute exception if the 'changes' column does
        not exist, most likely because TransactionChangesPlugin is not enabled.
        """
        if hasattr(self, "changes"):
            return [changes.entity_name for changes in self.changes]
        else:
            raise NoChangesAttribute()

    @property
    def changed_entities(self):
        """Return all changed entities for this transaction log entry.

        Entities are returned as a dict where keys are entity classes and
        values lists of entitites that changed in this transaction.
        """
        manager = self.__versioning_manager__
        tuples = set(manager.version_class_map.items())
        entities = {}

        session = sa.orm.object_session(self)

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

    @property
    def restore_db_state(self) -> dict:
        """
        Gives you a dictionary having keys as table_name and values as list for any particular transaction.

        """
        manager = self.__versioning_manager__
        tuples = set(manager.version_class_map.items())
        # FIXME: Need to add Table handle manager to support option for table.!
        # tuples = tuples.union(set(manager.version_table_map.items()))
        entities = {}

        session = sa.orm.object_session(self)
        for class_or_table, version_class_or_table in tuples:

            tx_column = manager.option(class_or_table, "transaction_column_name")
            operation_type_column_name = manager.option(class_or_table, "operation_type_column_name")
            # Get the primary_keys for version_class
            primary_keys = get_primary_keys(class_or_table)

            # To get state of object that are being traced we get
            # Closest transaction ID in version class by grouping over primary key of class.
            entities[version_class_or_table] = (
                session.query(version_class_or_table)
                .where(
                    getattr(version_class_or_table, tx_column) <= self.id,
                )
                .group_by(*primary_keys)
                .having(
                    sa.and_(
                        # NOTE: We don't want deleted objects or do we?
                        # state of DB should not provide the deleted object or shall it inform that
                        # this object is deleted via operation_type col?
                        getattr(version_class_or_table, operation_type_column_name) != Operation.DELETE,
                        sa.func.max(getattr(version_class_or_table, tx_column))
                        == getattr(version_class_or_table, tx_column),
                    )
                )
            ).all()
        # TODO: The entities currently being returned as a dictionary {'table_name': [..., ...], 'table_name2': [..., ...]},
        # - want to return a custom/scoped_session where user can use this session object to query these entities on fly(in memory?).
        # - ...
        return entities


class TransactionFactory(ModelFactory):
    model_name = "Transaction"

    def __init__(self, remote_addr=True):
        self.remote_addr = remote_addr

    def create_class(self, manager):
        """Create Transaction class."""

        class Transaction(manager.declarative_base, TransactionBase):
            __tablename__ = "transaction"
            __versioning_manager__ = manager

            id = sa.Column(
                sa.types.BigInteger,
                sa.schema.Sequence("transaction_id_seq"),
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
                    except KeyError:
                        raise ImproperlyConfigured(
                            "Could not build relationship between Transaction"
                            " and %s. %s was not found in declarative class "
                            "registry. Either configure VersioningManager to "
                            "use different user class or disable this "
                            "relationship " % (user_cls, user_cls)
                        )

                user_id = sa.Column(
                    sa.inspect(user_cls).primary_key[0].type,
                    sa.ForeignKey(sa.inspect(user_cls).primary_key[0]),
                    index=True,
                )

                user = sa.orm.relationship(user_cls)

            def __repr__(self):
                fields = ["id", "issued_at", "user"]
                field_values = OrderedDict(
                    (field, getattr(self, field)) for field in fields if hasattr(self, field)
                )
                return "<Transaction %s>" % ", ".join(
                    (
                        "%s=%r" % (field, value) if not isinstance(value, int)
                        # We want the following line to ensure that longs get
                        # shown without the ugly L suffix on python 2.x
                        # versions
                        else "%s=%d" % (field, value)
                        for field, value in field_values.items()
                    )
                )

        return Transaction
