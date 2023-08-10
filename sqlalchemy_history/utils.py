from itertools import chain
from inspect import isclass
from collections import defaultdict

import sqlalchemy as sa
from sqlalchemy.orm.attributes import get_history
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy_utils.functions import (
    get_primary_keys,
    identity,
    naturally_equivalent,
)

from sqlalchemy_history.exc import ClassNotVersioned, TableNotVersioned


def get_versioning_manager(item):
    """
    Return the associated SQLAlchemy-History VersioningManager for given
    SQLAlchemy declarative model class or object or table.

    :param item: An item from SQLAlchemy
    :param A: declarative ORM object
    :param A: declarative ORM class
    :param An: instance of a SQL table
    :returns: SQLAlchemy declarative model class or object or table.

    """
    # The ORM class or SQL table on which versioning was enabled
    versioned_item = None
    if isclass(item):
        versioned_item = item
    else:
        if isinstance(item, AliasedClass):
            versioned_item = sa.inspect(item).mapper.class_
        elif isinstance(item, sa.Table):
            versioned_item = item
        else:
            versioned_item = item.__class__

    try:
        return versioned_item.__versioning_manager__
    except AttributeError:
        if isinstance(versioned_item, sa.Table):
            raise TableNotVersioned('Table "%s"' % versioned_item.name)
        else:
            raise ClassNotVersioned(versioned_item.__name__)


def option(obj_or_class, option_name):
    """Return the option value of given option for given versioned object or class.

    :param obj_or_class: SQLAlchemy declarative model object or class
    :param option_name: The name of an option to return

    """
    if isinstance(obj_or_class, AliasedClass):
        obj_or_class = sa.inspect(obj_or_class).mapper.class_
    cls = obj_or_class if isclass(obj_or_class) else obj_or_class.__class__
    if not hasattr(cls, "__versioned__"):
        cls = parent_class(cls)
    return get_versioning_manager(cls).option(cls, option_name)


def tx_column_name(obj):
    return option(obj, "transaction_column_name")


def end_tx_column_name(obj):
    return option(obj, "end_transaction_column_name")


def end_tx_attr(obj):
    return getattr(obj.__class__, end_tx_column_name(obj))


def parent_class(version_cls):
    """
    Return the parent class for given version model class.

    :param model: SQLAlchemy declarative version model class
    :param version_cls:
    :returns:
    """
    manager = get_versioning_manager(version_cls)
    try:
        return next((k for k, v in manager.version_class_map.items() if v == version_cls))
    except StopIteration:
        # Should raise Key Error if we can't find the parent_object of a orphaned versioned_model
        raise KeyError(version_cls)


def parent_table(version_table):
    """
    Return corresponding parent table for any given parent table.

    :param version_table: A versioned table table which could be either association_table or model_table.
    """
    manager = get_versioning_manager(version_table)
    try:
        return next((k for k, v in manager.version_table_map.items() if v == version_table))
    except StopIteration:
        # Raise Key error as we couldn't find parent_object of versioned_object
        raise KeyError(version_table)


def transaction_class(cls):
    """
    Return the associated transaction class for given versioned SQLAlchemy
    declarative class or version class.

    :param cls: SQLAlchemy versioned declarative class or version model class
    :returns: declarative class or version class.
    """
    return get_versioning_manager(cls).transaction_cls


def version_obj(session, parent_obj):
    manager = get_versioning_manager(parent_obj)
    uow = manager.unit_of_work(session)
    for version_obj in uow.version_session:
        if parent_class(version_obj.__class__) == parent_obj.__class__ and identity(version_obj)[
            :-1
        ] == identity(parent_obj):
            return version_obj


def version_class(model):
    """
    Return the version class for given SQLAlchemy declarative model class.

    :param model: SQLAlchemy declarative model class
    :returns:
    """
    manager = get_versioning_manager(model)
    return manager.version_class_map.get(model, None)


def version_table(table):
    """
    Return associated version table for given SQLAlchemy Table object.

    :param table: SQLAlchemy Table object

    """
    manager = get_versioning_manager(table)
    return manager.version_table_map.get(table, None)


def versioned_objects(session):
    """
    Return all versioned objects in given session.

    :param session: SQLAlchemy session object

    """
    for obj in session:
        if is_versioned(obj):
            yield obj


def is_versioned(obj_or_class):
    """
    Return whether or not given object is versioned.

    :param obj_or_class:
    :param SQLAlchemy: declarative model object or SQLAlchemy declarative model
    :param class:
    :param seealso: func
    :returns:
    """
    try:
        return hasattr(obj_or_class, "__versioned__") and get_versioning_manager(obj_or_class).option(
            obj_or_class, "versioning"
        )
    except ClassNotVersioned:
        return False


def versioned_column_properties(obj_or_class):
    """

    :param obj: SQLAlchemy declarative model object
    :param obj_or_class:
    :returns: declarative model object.

    """
    manager = get_versioning_manager(obj_or_class)

    cls = obj_or_class if isclass(obj_or_class) else obj_or_class.__class__

    mapper = sa.inspect(cls)
    for key, column in mapper.columns.items():
        # Ignores non table columns
        if not is_table_column(column):
            continue

        if not manager.is_excluded_property(obj_or_class, key):
            yield getattr(mapper.attrs, key)


def versioned_relationships(obj, versioned_column_keys):
    """

    :param obj: SQLAlchemy declarative model object
    :param versioned_column_keys:
    :returns: declarative model object.

    """
    for prop in sa.inspect(obj.__class__).relationships:
        if any(c.key in versioned_column_keys for c in prop.local_columns):
            yield prop


def vacuum(session, model, yield_per=1000):
    """When making structural changes to version tables (for example dropping
    columns) there are sometimes situations where some old version records
    become futile.

    Vacuum deletes all futile version rows which had no changes compared to
    previous version.


    :param session: SQLAlchemy session object
    :param model: SQLAlchemy declarative model class
    :param yield_per: how many rows to process at a time (Default value = 1000)
    """
    version_cls = version_class(model)
    versions = defaultdict(list)

    query = (session.query(version_cls).order_by(option(version_cls, "transaction_column_name"))).yield_per(
        yield_per
    )

    primary_key_col = sa.inspection.inspect(model).primary_key[0].name

    for version in query:
        version_id = getattr(version, primary_key_col)
        if versions[version_id]:
            prev_version = versions[version_id][-1]
            if naturally_equivalent(prev_version, version):
                session.delete(version)
        else:
            versions[version_id].append(version)


def is_table_column(column):
    """
    Return wheter of not give field is a column over the database table.

    :param column: SQLAclhemy model field
    :returns: Bool

    """
    return isinstance(column, sa.Column)


def is_internal_column(model, column_name):
    """
    Return whether or not given column of given SQLAlchemy declarative classs
    is considered an internal column (a column whose purpose is mainly
    for SQLA-History's internal use).

    :param version_obj: SQLAlchemy declarative class
    :param column_name: Name of the column
    :param model:
    :returns: Bool

    """
    return column_name in (
        option(model, "transaction_column_name"),
        option(model, "end_transaction_column_name"),
        option(model, "operation_type_column_name"),
    )


def is_modified_or_deleted(obj):
    """
    Return whether or not some of the versioned properties of given SQLAlchemy
    declarative object have been modified or if the object has been deleted.

    :param obj: SQLAlchemy declarative model object
    :returns: Bool

    """
    session = sa.orm.object_session(obj)
    return is_versioned(obj) and (is_modified(obj) or obj in chain(session.deleted, session.new))


def is_modified(obj):
    """
    Return whether or not the versioned properties of given object have been
    modified.

    :param obj: SQLAlchemy declarative model object
    :returns: modified.

    """
    column_names = sa.inspect(obj.__class__).columns.keys()
    versioned_column_keys = [prop.key for prop in versioned_column_properties(obj)]
    versioned_relationship_keys = [prop.key for prop in versioned_relationships(obj, versioned_column_keys)]
    for key, attr in sa.inspect(obj).attrs.items():
        if key in column_names:
            if key not in versioned_column_keys:
                continue
            if attr.history.has_changes():
                return True
        if key in versioned_relationship_keys:
            if attr.history.has_changes():
                return True
    return False


def is_session_modified(session):
    """Return whether or not any of the versioned objects in given session have
    been either modified or deleted.

    :param session: SQLAlchemy session object
    :returns: Bool

    """
    return any(is_modified_or_deleted(obj) for obj in versioned_objects(session))


def count_versions(obj):
    """
    Return the number of versions given object has. This function works even
    when obj has `create_models` and `create_tables` versioned settings


    :param obj: SQLAlchemy declarative model object
    :returns: when obj has `create_models` and `create_tables` versioned settings
    disabled.


    """
    session = sa.orm.object_session(obj)
    if session is None:
        # If object is transient, we assume it has no version history.
        return 0
    manager = get_versioning_manager(obj)
    table_name = manager.option(obj, "table_name") % obj.__table__.name
    criteria = ["%s = %r" % (pk, getattr(obj, pk)) for pk in get_primary_keys(obj)]
    query = sa.text("SELECT COUNT(1) FROM %s WHERE %s" % (table_name, " AND ".join(criteria)))
    return session.execute(query).scalar()


def changeset(obj):
    """
    Return a humanized changeset for given SQLAlchemy declarative object. With
    this function you can easily check the changeset of given object in current
    transaction.

    :param obj:
    :returns: this function you can easily check the changeset of given object in current
    transaction.

    """
    data = {}
    session = sa.orm.object_session(obj)
    if session and obj in session.deleted:
        columns = [c for c in sa.inspect(obj.__class__).columns.values() if is_table_column(c)]

        for column in columns:
            if not column.primary_key:
                value = getattr(obj, column.key)
                if value is not None:
                    data[column.key] = [None, getattr(obj, column.key)]
    else:
        for prop in obj.__mapper__.iterate_properties:
            history = get_history(obj, prop.key)
            if history.has_changes():
                old_value = history.deleted[0] if history.deleted else None
                new_value = history.added[0] if history.added else None

                if new_value:
                    data[prop.key] = [new_value, old_value]
    return data


class VersioningClauseAdapter(sa.sql.visitors.ReplacingCloningVisitor):
    def replace(self, col):
        if isinstance(col, sa.Column):
            table = version_table(col.table)
            return table.c.get(col.key)


def adapt_columns(expr):
    return VersioningClauseAdapter().traverse(expr)


def get_association_proxies(klass):
    """Get Association proxy mappings for ORM Models"""
    # NOTE: Ideally this method we should try to move it to sqlalchemy-utils
    # if they are ok with it as they provide a similar method to detect and
    # provide hypbrid properties.
    # ref: https://github.com/kvesteri/sqlalchemy-utils/issues/679
    association_proxy_mapping = {}
    for key, prop in sa.inspect(klass).all_orm_descriptors.items():
        if isinstance(prop, sa.ext.associationproxy.AssociationProxy):
            association_proxy_mapping[key] = prop
    return association_proxy_mapping
