"""Transaction model makes transactions for history tables
"""

from datetime import datetime

from collections import OrderedDict
import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

from sqlalchemy_history.exc import ImproperlyConfigured, NoChangesAttribute
from sqlalchemy_history.factory import ModelFactory


@compiles(sa.types.BigInteger, "sqlite")
def compile_big_integer(element, compiler, **kw):
    return "INTEGER"


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
                sa.schema.Sequence("transaction_id_seq", start=1),
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
