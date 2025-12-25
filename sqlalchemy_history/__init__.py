"""
Modules exported by this package:

- `make_versioned`: This is the public API function of SQLAlchemy-History for making certain mappers and
 sessions versioned.

- `remove_versioning`: Remove the versioning from given mapper / session and manager.
"""

from __future__ import annotations

import typing as t

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Mapper, Session

from sqlalchemy_history.exc import (  # noqa: F401
    ClassNotVersioned,
    ImproperlyConfigured,
    TableNotVersioned,
)
from sqlalchemy_history.manager import VersioningManager
from sqlalchemy_history.operation import Operation  # noqa: F401
from sqlalchemy_history.transaction import TransactionFactory  # noqa: F401
from sqlalchemy_history.unit_of_work import UnitOfWork  # noqa: F401
from sqlalchemy_history.utils import (  # noqa: F401
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


if t.TYPE_CHECKING:
    from sqlalchemy_history._typing import VersioningOptions
    from sqlalchemy_history.plugins.base import Plugin

__version__ = "2.1.4"


versioning_manager = VersioningManager()


def make_versioned(
    mapper: Mapper = Mapper,
    session: Session = Session,
    manager: VersioningManager = versioning_manager,
    plugins: list[type[Plugin]] | None = None,
    options: VersioningOptions | None = None,
    user_cls: str | None = "User",
) -> None:
    """This is the public API function of SQLAlchemy-History for making certain mappers and sessions
     versioned.
    By default this applies to all mappers and all sessions.

    **Examples**

        >>> make_versioned(user_cls=None, options={'table_name': '%_tracker'})
        None

    :param mapper: SQLAlchemy mapper to apply the versioning to. (Default value = sa.orm.Mapper)
    :type mapper: sa.orm.Mapper
    :param session: SQLAlchemy session to apply the versioning to. By default this is
     sa.orm.session.Session
     meaning it applies to all Session subclasses.
    :param manager: SQLAlchemy-History versioning manager. (Default value = versioning_manager)
    :type manager: VersioningManager
    :param plugins: Plugins to pass for versioning manager. (Default value = None)
    :param options: A dictionary of VersioningManager options. (Default value = None)
    :type options: dict
    :param user_cls: User class which the Transaction class should have relationship to.
            This can either be a class or string name of a class for lazy
            evaluation. (Default value = "User")

    :returns: None
    :rtype: NoneType
    """
    if plugins is not None:
        manager.plugins = plugins

    if options is not None:
        manager.options.update(options)

    manager.user_cls = user_cls
    manager.apply_class_configuration_listeners(mapper)
    manager.track_operations(mapper)
    manager.track_session(session)

    event.listen(sa.engine.Engine, "before_cursor_execute", manager.track_sql_operations)

    event.listen(sa.engine.Engine, "rollback", manager.clear_connection)

    event.listen(
        sa.engine.Engine,
        "set_connection_execution_options",
        manager.track_cloned_connections,
    )


def remove_versioning(
    mapper: Mapper = Mapper,
    session: Session = Session,
    manager: VersioningManager = versioning_manager,
) -> None:
    """Remove the versioning from given mapper / session and manager.

    **Examples**

        >>> remove_versioning()
        None

    :param mapper: SQLAlchemy mapper to remove the versioning from. (Default value = sa.orm.Mapper)
    :type mapper: sa.orm.Mapper
    :param session: SQLAlchemy session to remove the versioning from. By default this is
                    sa.orm.session.Session meaning it applies to all sessions.
                     (Default value = sa.orm.session.Session)
    :param manager: SQLAlchemy-History versioning manager. (Default value = versioning_manager)
    :type manager: VersioningManager

    :returns: None
    :rtype: NoneType
    """
    manager.reset()
    manager.remove_class_configuration_listeners(mapper)
    manager.remove_operations_tracking(mapper)
    manager.remove_session_tracking(session)
    event.remove(sa.engine.Engine, "before_cursor_execute", manager.track_sql_operations)

    event.remove(sa.engine.Engine, "rollback", manager.clear_connection)

    event.remove(
        sa.engine.Engine,
        "set_connection_execution_options",
        manager.track_cloned_connections,
    )
