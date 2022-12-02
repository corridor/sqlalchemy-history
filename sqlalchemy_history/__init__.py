"""
Modules exported by this package:

- `make_versioned`: This is the public API function of SQLAlchemy-History for making certain mappers and sessions versioned.

- `remove_versioning`: Remove the versioning from given mapper / session and manager.
"""

import sqlalchemy as sa
from sqlalchemy_history.exc import ClassNotVersioned, ImproperlyConfigured
from sqlalchemy_history.manager import VersioningManager
from sqlalchemy_history.operation import Operation
from sqlalchemy_history.transaction import TransactionFactory
from sqlalchemy_history.unit_of_work import UnitOfWork
from sqlalchemy_history.utils import (
    changeset,
    count_versions,
    get_versioning_manager,
    is_modified,
    is_session_modified,
    parent_class,
    transaction_class,
    tx_column_name,
    vacuum,
    version_class,
)


__version__ = "2.0.0.rc1"


versioning_manager = VersioningManager()


def make_versioned(
    mapper=sa.orm.mapper,
    session=sa.orm.session.Session,
    manager=versioning_manager,
    plugins=None,
    options=None,
    user_cls="User",
):
    """This is the public API function of SQLAlchemy-History for making certain mappers and sessions versioned.
    By default this applies to all mappers and all sessions.

    Examples:
        >>> make_versioned(user_cls=None, options={'table_name': '%_tracker'})
        None

    :param mapper: SQLAlchemy mapper to apply the versioning to. (Default value = sa.orm.mapper)
    :param session: SQLAlchemy session to apply the versioning to. By default this is sa.orm.session.Session meaning it applies to all Session subclasses.
    :param manager: SQLAlchemy-History versioning manager. (Default value = versioning_manager)
    :param plugins: Plugins to pass for versioning manager. (Default value = None)
    :param options: A dictionary of VersioningManager options. (Default value = None)
    :param user_cls: User class which the Transaction class should have relationship to.
            This can either be a class or string name of a class for lazy
            evaluation. (Default value = "User")
    :returns: None
    """
    if plugins is not None:
        manager.plugins = plugins

    if options is not None:
        manager.options.update(options)

    manager.user_cls = user_cls
    manager.apply_class_configuration_listeners(mapper)
    manager.track_operations(mapper)
    manager.track_session(session)

    sa.event.listen(sa.engine.Engine, "before_cursor_execute", manager.track_association_operations)

    sa.event.listen(sa.engine.Engine, "rollback", manager.clear_connection)

    sa.event.listen(
        sa.engine.Engine,
        "set_connection_execution_options",
        manager.track_cloned_connections,
    )


def remove_versioning(mapper=sa.orm.mapper, session=sa.orm.session.Session, manager=versioning_manager):
    """Remove the versioning from given mapper / session and manager.

    Examples:
        >>> remove_versioning()

    :param mapper: SQLAlchemy mapper to remove the versioning from. (Default value = sa.orm.mapper)
    :param session: SQLAlchemy session to remove the versioning from. By default this is
                    sa.orm.session.Session meaning it applies to all sessions. (Default value = sa.orm.session.Session)
    :param manager: SQLAlchemy-History versioning manager. (Default value = versioning_manager)
    """
    manager.reset()
    manager.remove_class_configuration_listeners(mapper)
    manager.remove_operations_tracking(mapper)
    manager.remove_session_tracking(session)
    sa.event.remove(sa.engine.Engine, "before_cursor_execute", manager.track_association_operations)

    sa.event.remove(sa.engine.Engine, "rollback", manager.clear_connection)

    sa.event.remove(
        sa.engine.Engine,
        "set_connection_execution_options",
        manager.track_cloned_connections,
    )
