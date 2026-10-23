"""Utilities vendored from SQLAlchemy-Utils; see SQLAlchemy-Continuum's _compat module.

Only helpers used by SQLAlchemy-History are retained. Generic relationships use
public inspection and hybrid APIs for compatibility with SQLAlchemy 2.0 and 2.1.

Reference: https://github.com/sqlalchemy-continuum/sqlalchemy-continuum/blob/main/sqlalchemy_continuum/_compat.py
The original SQLAlchemy-Utils copyright and license are reproduced in LICENSE.
"""

import json
from collections import OrderedDict
from collections.abc import Iterable
from inspect import isclass

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.orm import ColumnProperty, MappedColumn, Mapper, object_session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.orm.util import AliasedClass, AliasedInsp

from sqlalchemy_history.exc import ImproperlyConfigured


try:
    from sqlalchemy.dialects.postgresql import JSON

    has_postgres_json = True
except ImportError:

    class PostgresJSONType(sa.types.UserDefinedType):
        """
        Text search vector type for postgresql.
        """

        def get_col_spec(self):
            return "json"

    ischema_names["json"] = PostgresJSONType
    has_postgres_json = False


def identity(obj_or_class):
    """
    Return the identity of given sqlalchemy declarative model class or instance
    as a tuple. This differs from obj._sa_instance_state.identity in a way that
    it always returns the identity even if object is still in transient state (
    new object that is not yet persisted into database). Also for classes it
    returns the identity attributes.

    ::

        from sqlalchemy import inspect
        from sqlalchemy_history._compat.sqlalchemy_utils import identity


        user = User(name='John Matrix')
        session.add(user)
        identity(user)  # None
        inspect(user).identity  # None

        session.flush()  # User now has id but is still in transient state

        identity(user)  # (1,)
        inspect(user).identity  # None

        session.commit()

        identity(user)  # (1,)
        inspect(user).identity  # (1, )


    You can also use identity for classes::


        identity(User)  # (User.id, )

    .. versionadded: 0.21.0

    :param obj: SQLAlchemy declarative model object
    """
    return tuple(getattr(obj_or_class, column_key) for column_key in get_primary_keys(obj_or_class))


def get_primary_keys(mixed):
    """
    Return an OrderedDict of all primary keys for given Table object,
    declarative class or declarative class instance.

    :param mixed:
        SA Table object, SA declarative class or SA declarative class instance

    ::

        get_primary_keys(User)

        get_primary_keys(User())

        get_primary_keys(User.__table__)

        get_primary_keys(User.__mapper__)

        get_primary_keys(sa.orm.aliased(User))

        get_primary_keys(sa.orm.aliased(User.__table__))


    .. versionchanged: 0.25.3
        Made the function return an ordered dictionary instead of generator.
        This change was made to support primary key aliases.

        Renamed this function to 'get_primary_keys', formerly 'primary_keys'

    .. seealso:: :func:`get_columns`
    """
    return OrderedDict(((key, column) for key, column in get_columns(mixed).items() if column.primary_key))


def naturally_equivalent(obj, obj2):
    """
    Returns whether or not two given SQLAlchemy declarative instances are
    naturally equivalent (all their non primary key properties are equivalent).


    ::

        from sqlalchemy_history._compat.sqlalchemy_utils import naturally_equivalent


        user = User(name='someone')
        user2 = User(name='someone')

        user == user2  # False

        naturally_equivalent(user, user2)  # True


    :param obj: SQLAlchemy declarative model object
    :param obj2: SQLAlchemy declarative model object to compare with `obj`
    """
    for column_key, column in sa.inspect(obj.__class__).columns.items():
        if column.primary_key:
            continue

        if getattr(obj, column_key) != getattr(obj2, column_key):
            return False
    return True


def get_columns(mixed):  # noqa: PLR0911
    """
    Return a collection of all Column objects for given SQLAlchemy
    object.

    The type of the collection depends on the type of the object to return the
    columns from.

    ::

        get_columns(User)

        get_columns(User())

        get_columns(User.__table__)

        get_columns(User.__mapper__)

        get_columns(sa.orm.aliased(User))

        get_columns(sa.orm.alised(User.__table__))


    :param mixed:
        SA Table object, SA Mapper, SA declarative class, SA declarative class
        instance or an alias of any of these objects
    """
    if isinstance(mixed, sa.SelectBase):
        return mixed.selected_columns
    if isinstance(mixed, sa.Selectable):
        return mixed.c
    if isinstance(mixed, AliasedClass):
        return sa.inspect(mixed).mapper.columns
    if isinstance(mixed, Mapper):
        return mixed.columns
    if isinstance(mixed, InstrumentedAttribute):
        return mixed.property.columns
    if isinstance(mixed, ColumnProperty):
        return mixed.columns
    if isinstance(mixed, sa.Column):
        return [mixed]
    if not isclass(mixed):
        mixed = mixed.__class__
    return sa.inspect(mixed).columns


def get_column_key(model, column):
    """
    Return the key for given column in given model.

    :param model: SQLAlchemy declarative model object

    ::

        class User(Base):
            __tablename__ = 'user'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column('_name', sa.String)


        get_column_key(User, User.__table__.c._name)  # 'name'

    .. versionadded: 0.26.5

    .. versionchanged: 0.27.11
        Throws UnmappedColumnError instead of ValueError when no property was
        found for given column. This is consistent with how SQLAlchemy works.
    """
    mapper = sa.inspect(model)
    try:
        return mapper.get_property_by_column(column).key
    except UnmappedColumnError:
        for key, c in mapper.columns.items():
            if c.name == column.name and c.table is column.table:
                return key
    raise UnmappedColumnError(f"No column {column} is configured on mapper {mapper}...")


def get_declarative_base(model):
    """
    Returns the declarative base for given model class.

    :param model: SQLAlchemy declarative model
    """
    for parent in model.__bases__:
        try:
            parent.metadata  # noqa: B018
            return get_declarative_base(parent)
        except AttributeError:  # noqa: PERF203
            pass
    return model


def get_hybrid_properties(model):
    """
    Returns a dictionary of hybrid property keys and hybrid properties for
    given SQLAlchemy declarative model / mapper.


    Consider the following model

    ::


        from sqlalchemy.ext.hybrid import hybrid_property


        class Category(Base):
            __tablename__ = 'category'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.Unicode(255))

            @hybrid_property
            def lowercase_name(self):
                return self.name.lower()

            @lowercase_name.expression
            def lowercase_name(cls):
                return sa.func.lower(cls.name)


    You can now easily get a list of all hybrid property names

    ::


        from sqlalchemy_history._compat.sqlalchemy_utils import get_hybrid_properties


        get_hybrid_properties(Category).keys()  # ['lowercase_name']


    This function also supports aliased classes

    ::


        get_hybrid_properties(
            sa.orm.aliased(Category)
        ).keys()  # ['lowercase_name']


    .. versionchanged: 0.26.7
        This function now returns a dictionary instead of generator

    .. versionchanged: 0.30.15
        Added support for aliased classes

    :param model: SQLAlchemy declarative model or mapper
    """
    return {
        key: prop
        for key, prop in sa.inspect(model).mapper.all_orm_descriptors.items()
        if isinstance(prop, hybrid_property)
    }


def _generic_repr_method(self, fields):
    state = sa.inspect(self)
    field_reprs = []
    if not fields:
        fields = state.mapper.columns.keys()
    for key in fields:
        value = state.attrs[key].loaded_value
        value = "<not loaded>" if key in state.unloaded else repr(value)
        field_reprs.append(f"{key}={value}")

    return "{}({})".format(self.__class__.__name__, ", ".join(field_reprs))


def generic_repr(*fields):
    """Adds generic ``__repr__()`` method to a declarative SQLAlchemy model.

    In case if some fields are not loaded from a database, it doesn't
    force their loading and instead repesents them as ``<not loaded>``.

    In addition, user can provide field names as arguments to the decorator
    to specify what fields should present in the string representation
    and in what order.

    Example::


        import sqlalchemy as sa
        from sqlalchemy_history._compat.sqlalchemy_utils import generic_repr


        @generic_repr
        class MyModel(Base):
            __tablename__ = 'mymodel'
            id = sa.Column(sa.Integer, primary_key=True)
            name = sa.Column(sa.String)
            category = sa.Column(sa.String)

        session.add(MyModel(name='Foo', category='Bar'))
        session.commit()
        foo = session.query(MyModel).options(sa.orm.defer('category')).one(s)

        assert repr(foo) == 'MyModel(id=1, name='Foo', category=<not loaded>)'
    """
    if len(fields) == 1 and callable(fields[0]):
        target = fields[0]
        target.__repr__ = lambda self: _generic_repr_method(self, fields=None)
        return target

    def decorator(cls):
        cls.__repr__ = lambda self: _generic_repr_method(self, fields=fields)
        return cls

    return decorator


def has_changes(obj, attrs=None, exclude=None):
    """
    Simple shortcut function for checking if given attributes of given
    declarative model object have changed during the session. Without
    parameters this checks if given object has any modificiations. Additionally
    exclude parameter can be given to check if given object has any changes
    in any attributes other than the ones given in exclude.


    ::


        from sqlalchemy_history._compat.sqlalchemy_utils import has_changes


        user = User()

        has_changes(user, 'name')  # False

        user.name = 'someone'

        has_changes(user, 'name')  # True

        has_changes(user)  # True


    You can check multiple attributes as well.
    ::


        has_changes(user, ['age'])  # True

        has_changes(user, ['name', 'age'])  # True


    This function also supports excluding certain attributes.

    ::

        has_changes(user, exclude=['name'])  # False

        has_changes(user, exclude=['age'])  # True

    .. versionchanged: 0.26.6
        Added support for multiple attributes and exclude parameter.

    :param obj: SQLAlchemy declarative model object
    :param attrs: Names of the attributes
    :param exclude: Names of the attributes to exclude
    """
    if attrs:
        if isinstance(attrs, str):
            return sa.inspect(obj).attrs.get(attrs).history.has_changes()
        return any(has_changes(obj, attr) for attr in attrs)
    if exclude is None:
        exclude = []
    return any(attr.history.has_changes() for key, attr in sa.inspect(obj).attrs.items() if key not in exclude)


class JSONType(sa.types.TypeDecorator):
    """
    JSONType offers way of saving JSON data structures to database. On
    PostgreSQL the underlying implementation of this data type is 'json' while
    on other databases its simply 'text'.

    ::


        from sqlalchemy_history._compat.sqlalchemy_utils import JSONType


        class Product(Base):
            __tablename__ = 'product'
            id = sa.Column(sa.Integer, autoincrement=True)
            name = sa.Column(sa.Unicode(50))
            details = sa.Column(JSONType)


        product = Product()
        product.details = {
            'color': 'red',
            'type': 'car',
            'max-speed': '400 mph'
        }
        session.commit()
    """

    impl = sa.UnicodeText
    hashable = False
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # Use the native JSON type.
            if has_postgres_json:
                return dialect.type_descriptor(JSON())
            return dialect.type_descriptor(PostgresJSONType())
        return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql" and has_postgres_json:
            return value
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is not None:
            value = json.loads(value)
        return value


class GenericComparator(Comparator):
    def __init__(self, relationship, cls):
        self.relationship = relationship
        self.cls = cls

    def __clause_element__(self):
        raise NotImplementedError(
            "A generic relationship can only be compared against a model instance or with is_type()."
        )

    def __eq__(self, other):
        discriminator, ids = self.relationship._attributes(self.cls)
        q = discriminator == type(other).__name__
        for column, value in zip(ids, identity(other), strict=False):
            q &= column == value
        return q

    def __ne__(self, other):
        return ~(self == other)

    def is_type(self, other):
        discriminator, _ = self.relationship._attributes(self.cls)
        class_names = [mapper.class_.__name__ for mapper in sa.inspect(other).self_and_descendants]
        return discriminator.in_(class_names)


class GenericRelationship:
    """A generic form of the relationship property.

    Creates a 1 to many relationship between the parent model
    and any other models using a discriminator (the class name).

    Implemented as a hybrid property on top of the discriminator and id
    attributes, so it only relies on public SQLAlchemy APIs.

    :param discriminator:
        Field to discriminate which model we are referring to.
    :param id:
        Field to point to the model we are referring to.
    """

    def __init__(self, discriminator, id_):
        self.discriminator = discriminator
        if isinstance(id_, Iterable) and not isinstance(id_, str):
            self.ids = list(id_)
        else:
            self.ids = [id_]
        # Key for caching the assigned target object on the instance dict.
        self.cache_key = f"_generic_relationship_{id(self)}"

    def _key(self, cls, column):
        if isinstance(column, str):
            return column
        if isinstance(column, InstrumentedAttribute):
            return column.key
        if isinstance(column, hybrid_property):
            return column.__name__
        if isinstance(column, MappedColumn):
            column = column.column

        inspected = sa.inspect(cls)

        # AliasedClass produces AliasedInsp rather than Mapper.
        mapper = inspected.mapper if isinstance(inspected, AliasedInsp) else inspected
        try:
            return mapper.get_property_by_column(column).key
        except UnmappedColumnError as exc:
            raise ImproperlyConfigured(f"Could not find generic relationship attribute for {column!r}.") from exc

    def _keys(self, cls):
        return (
            self._key(cls, self.discriminator),
            [self._key(cls, column) for column in self.ids],
        )

    def _attributes(self, cls):
        discriminator, ids = self._keys(cls)
        return getattr(cls, discriminator), [getattr(cls, key) for key in ids]

    def _target_class(self, cls, discriminator):
        for mapper in sa.inspect(cls).registry.mappers:
            if mapper.class_.__name__ == discriminator:
                return mapper.class_
        return None

    def get(self, obj):
        discriminator_key, id_keys = self._keys(type(obj))
        expired = sa.inspect(obj).expired_attributes
        if discriminator_key in expired or any(key in expired for key in id_keys):
            obj.__dict__.pop(self.cache_key, None)
        discriminator = getattr(obj, discriminator_key)
        id_ = tuple(getattr(obj, key) for key in id_keys)

        # Return the object assigned to this relationship as long as the
        # discriminator and id still point to it.
        cached = obj.__dict__.get(self.cache_key)
        if (
            cached is not None
            and not sa.inspect(cached).was_deleted
            and type(cached).__name__ == discriminator
            and identity(cached) == id_
        ):
            return cached

        # Use the session the object is bound to in order to perform
        # a lazy query for the target.
        session = object_session(obj)
        if session is None:
            return None

        if all(value is None for value in id_):
            return None

        target_class = self._target_class(type(obj), discriminator)
        if target_class is None:
            # Unknown discriminator; return nothing.
            return None

        return session.get(target_class, id_)

    def set(self, obj, value):
        discriminator_key, id_keys = self._keys(type(obj))
        obj.__dict__[self.cache_key] = value

        if value is None:
            # Nullify relationship args
            for key in id_keys:
                setattr(obj, key, None)
            setattr(obj, discriminator_key, None)
        else:
            for key, pk in zip(id_keys, identity(value), strict=False):
                setattr(obj, key, pk)
            setattr(obj, discriminator_key, type(value).__name__)

    def comparator(self, cls):
        return GenericComparator(self, cls)


def generic_relationship(discriminator, id_, doc=None):
    relationship = GenericRelationship(discriminator, id_)
    prop = hybrid_property(
        relationship.get,
        relationship.set,
        custom_comparator=relationship.comparator,
    )
    prop.__doc__ = doc
    return prop
