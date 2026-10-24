"""Generic relationship scenarios based on SQLAlchemy-Utils, plus hybrid regressions.

Baseline: https://github.com/kvesteri/sqlalchemy-utils/tree/master/tests/generic_relationship
"""

from enum import Enum

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Session, aliased, declared_attr, mapped_column

from sqlalchemy_history._compat.sqlalchemy_utils import generic_relationship


class ObjectType(str, Enum):
    USER = "User"
    BUILDING = "Building"
    OFFICE = "Office"


@pytest.fixture(params=["plain", "column_alias", "composite", "abstract_base"])
def relationship_schema(request):
    return request.param


@pytest.fixture(params=[sa.Column, mapped_column], ids=["column", "mapped_column"])
def relationship_models(request, relationship_schema, engine):
    column = request.param
    composite = relationship_schema == "composite"

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "generic_user"
        id = column(sa.Integer, primary_key=True)
        if composite:
            code = column(sa.Integer, primary_key=True)

    class Building(Base):
        __tablename__ = "generic_building"
        id = column(sa.Integer, primary_key=True)
        if composite:
            code = column(sa.Integer, primary_key=True)

    if relationship_schema == "abstract_base":

        class EventBase(Base):
            __abstract__ = True
            object_type = column(sa.String(30))
            object_id = column(sa.Integer)

            @declared_attr
            @classmethod
            def object(cls):
                return generic_relationship("object_type", "object_id")

    else:
        EventBase = Base

    class Event(EventBase):
        __tablename__ = "generic_event"
        id = column(sa.Integer, primary_key=True)
        if relationship_schema != "abstract_base":
            object_type = column(
                "objectType" if relationship_schema == "column_alias" else "object_type", sa.String(30)
            )
            object_id = column(sa.Integer)
            if composite:
                object_code = column(sa.Integer)
                object = generic_relationship(object_type, (object_id, object_code))
            else:
                object = generic_relationship(object_type, object_id)

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session, Event, User, Building
    finally:
        Base.metadata.drop_all(engine)
        Base.registry.dispose()


def make_target(model, id_):
    values = {"id": id_}
    if hasattr(model, "code"):
        values["code"] = id_ + 10
    return model(**values)


def test_set_as_none(relationship_models):
    _, Event, _, _ = relationship_models
    event = Event()
    event.object = None
    assert event.object is None
    assert event.object_id is None
    assert event.object_type is None


def test_set_manual_and_get(relationship_models):
    session, Event, User, _ = relationship_models
    user = make_target(User, 1)
    session.add(user)
    session.commit()
    event = Event(id=1, object_id=user.id, object_type="User")
    if hasattr(event, "object_code"):
        event.object_code = user.code
    assert event.object is None
    session.add(event)
    session.commit()
    assert event.object is user


def test_set_and_get(relationship_models):
    session, Event, User, _ = relationship_models
    user = make_target(User, 1)
    session.add(user)
    session.commit()
    event = Event(id=1, object=user)
    assert event.object is user
    assert event.object_id == user.id
    assert event.object_type == "User"
    if hasattr(event, "object_code"):
        assert event.object_code == user.code
    session.add(event)
    session.commit()
    assert event.object is user


def test_compare_instance_and_query(relationship_models):
    session, Event, User, _ = relationship_models
    first, second = make_target(User, 1), make_target(User, 2)
    event = Event(id=1, object=first)
    session.add_all([first, second, event])
    session.commit()
    assert event.object == first
    assert event.object != second
    assert session.scalar(sa.select(Event).filter_by(object=first)) is event
    assert session.scalar(sa.select(Event).filter_by(object=second)) is None
    assert session.scalar(sa.select(Event).where(Event.object == second)) is None
    assert session.scalar(sa.select(Event).where(Event.object != second)) is event
    assert session.scalar(sa.select(Event).where(Event.object.is_type(User))) is event
    alias = aliased(Event)
    assert session.scalar(sa.select(alias).where(alias.object == first)) is event


def test_reassign_persistent_relationship(relationship_models):
    session, Event, User, _ = relationship_models
    first, second = make_target(User, 1), make_target(User, 2)
    event = Event(id=1, object=first)
    session.add_all([first, second, event])
    session.commit()
    event.object = second
    session.commit()
    session.expunge(event)
    assert session.get(Event, 1).object is second


def test_change_identifier(relationship_models):
    session, Event, User, _ = relationship_models
    first, second = make_target(User, 1), make_target(User, 2)
    event = Event(id=1, object=first)
    session.add_all([first, second, event])
    session.commit()
    event.object_id = second.id
    if hasattr(event, "object_code"):
        event.object_code = second.code
    assert event.object is second


def test_switch_target_model_with_same_identity(relationship_models):
    session, Event, User, Building = relationship_models
    user, building = make_target(User, 1), make_target(Building, 1)
    event = Event(id=1, object=user)
    session.add_all([user, building, event])
    session.commit()
    event.object = building
    session.commit()
    session.expunge(event)
    assert session.get(Event, 1).object is building


def test_clear_persistent_relationship(relationship_models):
    session, Event, User, _ = relationship_models
    user = make_target(User, 1)
    event = Event(id=1, object=user)
    session.add_all([user, event])
    session.commit()
    event.object = None
    session.commit()
    session.expunge(event)
    event = session.get(Event, 1)
    assert event.object is None
    assert event.object_id is None
    assert event.object_type is None
    if hasattr(event, "object_code"):
        assert event.object_code is None


@pytest.fixture(params=[sa.Column, mapped_column], ids=["column", "mapped_column"])
def inheritance_models(request, engine):
    column = request.param

    class Base(DeclarativeBase):
        pass

    class Employee(Base):
        __tablename__ = "generic_employee"
        id = column(sa.Integer, primary_key=True)
        kind = column(sa.String(30))
        __mapper_args__ = {"polymorphic_on": kind, "polymorphic_identity": "employee"}

    class Manager(Employee):
        __mapper_args__ = {"polymorphic_identity": "manager"}

    class Engineer(Employee):
        __mapper_args__ = {"polymorphic_identity": "engineer"}

    class Event(Base):
        __tablename__ = "generic_employee_event"
        id = column(sa.Integer, primary_key=True)
        object_type = column(sa.String(30))
        object_id = column(sa.Integer)
        object = generic_relationship(object_type, object_id)

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session, Event, Employee, Manager, Engineer
    finally:
        Base.metadata.drop_all(engine)
        Base.registry.dispose()


def test_inherited_target_assignment_and_queries(inheritance_models):
    session, Event, Employee, Manager, Engineer = inheritance_models
    manager, engineer = Manager(id=1), Engineer(id=2)
    first, second = Event(id=1, object=manager), Event(id=2, object=engineer)
    session.add_all([manager, engineer, first, second])
    session.commit()
    assert first.object is manager
    assert first.object != engineer
    assert first.object_type == "Manager"
    assert session.scalar(sa.select(Event).filter_by(object=manager)) is first
    assert session.scalar(sa.select(Event).where(Event.object != manager)) is second
    assert session.scalars(sa.select(Event).where(Event.object.is_type(Manager))).all() == [first]
    assert session.scalars(sa.select(Event).where(Event.object.is_type(Employee)).order_by(Event.id)).all() == [
        first,
        second,
    ]
    alias = aliased(Event)
    assert session.scalar(sa.select(alias).where(alias.object == manager)) is first
    first.object = engineer
    session.commit()
    session.expunge(first)
    first = session.get(Event, 1)
    assert first.object is engineer
    first.object = None
    session.commit()
    assert first.object is None


def test_inherited_target_manual_keys(inheritance_models):
    session, Event, _, Manager, _ = inheritance_models
    manager = Manager(id=1)
    session.add(manager)
    session.commit()
    event = Event(id=1, object_type="Manager", object_id=manager.id)
    assert event.object is None
    session.add(event)
    session.commit()
    assert event.object is manager


@pytest.mark.parametrize("column", [sa.Column, mapped_column], ids=["column", "mapped_column"])
def test_hybrid_history_relationship(engine, column):
    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "generic_history_user"
        id = column(sa.Integer, primary_key=True)

    class UserHistory(Base):
        __tablename__ = "generic_user_history"
        id = column(sa.Integer, primary_key=True)
        transaction_id = column(sa.Integer, primary_key=True)

    class Event(Base):
        __tablename__ = "generic_history_event"
        id = column(sa.Integer, primary_key=True)
        transaction_id = column(sa.Integer)
        object_type = column(sa.String(30))
        object_id = column(sa.Integer)
        object = generic_relationship(object_type, object_id)

        @hybrid_property
        def object_version_type(self):
            return self.object_type + "History"

        object_version = generic_relationship(object_version_type, (object_id, transaction_id))

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            user = User(id=1)
            first = UserHistory(id=1, transaction_id=1)
            second = UserHistory(id=1, transaction_id=2)
            session.add_all([user, first, second])
            session.commit()
            event = Event(id=1, object_type="User", object_id=1, transaction_id=1)
            assert event.object is None
            assert event.object_version is None
            session.add(event)
            session.commit()
            assert event.object is user
            assert event.object_version is first
            event.object_version = second
            session.commit()
            session.expunge(event)
            event = session.get(Event, 1)
            assert event.object_version is second
            assert event.transaction_id == 2
            assert event.object is user
            alias = aliased(Event)
            assert session.scalar(sa.select(alias).where(alias.object_version == second)) is event
    finally:
        Base.metadata.drop_all(engine)
        Base.registry.dispose()


@pytest.fixture(params=[sa.Column, mapped_column], ids=["column", "mapped_column"])
def hybrid_models(request, engine):
    column = request.param

    class Base(DeclarativeBase):
        pass

    class User(Base):
        __tablename__ = "generic_hybrid_user"
        id = column(sa.Integer, primary_key=True)

    class Building(Base):
        __tablename__ = "generic_hybrid_building"
        id = column(sa.Integer, primary_key=True)

    class Event(Base):
        __tablename__ = "generic_hybrid_event"
        id = column(sa.Integer, primary_key=True)
        object_type = column(
            sa.Enum(ObjectType, native_enum=False, values_callable=lambda enum: [item.value for item in enum])
        )
        object_id = column("object_pk", sa.Integer)

        _object_type_mapper = {
            ObjectType.USER: "User",
            ObjectType.BUILDING: "Building",
            ObjectType.OFFICE: "Building",
        }

        @hybrid_property
        def object_type_cls(self):
            return self._object_type_mapper.get(self.object_type)

        @object_type_cls.expression
        def object_type_cls(self):
            return sa.case(self._object_type_mapper, value=self.object_type, else_=None)

        object = generic_relationship(object_type_cls, object_id)
        by_name = generic_relationship("object_type_cls", "object_id")

    Event.by_attribute = generic_relationship(Event.object_type_cls, Event.object_id)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session, Event, User, Building
    Base.metadata.drop_all(engine)
    Base.registry.dispose()


@pytest.mark.parametrize("attribute", ["object", "by_name", "by_attribute"])
@pytest.mark.parametrize("object_first", [False, True])
def test_readonly_hybrid_assignment_and_reload(hybrid_models, attribute, object_first):
    session, Event, User, _ = hybrid_models
    target = User(id=1)
    # Both constructor orders must work before either object belongs to a session.
    values = {attribute: target, "object_type": ObjectType.USER}
    if not object_first:
        values = dict(reversed(list(values.items())))
    reference = Event(id=1, **values)
    assert getattr(reference, attribute) is target
    assert reference.object_id == target.id
    assert reference.object_type is ObjectType.USER
    session.add_all([target, reference])
    session.commit()
    session.expunge_all()
    reference = session.get(Event, 1)
    assert getattr(reference, attribute) is session.get(User, 1)


@pytest.mark.parametrize("object_type", [ObjectType.BUILDING, ObjectType.OFFICE])
def test_assignment_preserves_many_to_one_discriminator(hybrid_models, object_type):
    session, Event, _, Building = hybrid_models
    target = Building(id=1)
    reference = Event(id=1, object_type=object_type, object=target)
    assert reference.object_type is object_type
    session.add_all([target, reference])
    session.commit()
    assert reference.object is target
    assert reference.object_type is object_type


def test_hybrid_with_explicit_key_workaround(hybrid_models):
    session, Event, User, _ = hybrid_models
    # Support the explicit descriptor key workaround used with SQLAlchemy-Utils.
    sa.inspect(Event).all_orm_descriptors["object_type_cls"].key = "object_type_cls"
    target = User(id=1)
    reference = Event(id=1, object_type=ObjectType.USER)
    reference.object = target
    session.add_all([target, reference])
    session.commit()
    assert reference.object is target


def test_readonly_hybrid_reassignment_and_rollback(hybrid_models):
    session, Event, User, _ = hybrid_models
    first, second = User(id=1), User(id=2)
    reference = Event(id=1, object_type=ObjectType.USER, object=first)
    session.add_all([first, second, reference])
    session.commit()
    reference.object = second
    assert reference.object is second
    session.commit()
    session.refresh(reference)
    assert reference.object_id == second.id
    assert reference.object is second
    reference.object = first
    session.rollback()
    assert reference.object is second


def test_clearing_readonly_hybrid_relationship(hybrid_models):
    session, Event, User, _ = hybrid_models
    target = User(id=1)
    reference = Event(id=1, object_type=ObjectType.USER, object=target)
    session.add_all([target, reference])
    session.commit()
    reference.object = None
    assert reference.object is None
    assert reference.object_id is None
    assert reference.object_type is ObjectType.USER
    session.commit()
    assert reference.object is None


def test_changing_hybrid_backing_column_invalidates_target(hybrid_models):
    session, Event, User, Building = hybrid_models
    user, building = User(id=1), Building(id=1)
    reference = Event(id=1, object_type=ObjectType.USER, object=user)
    session.add_all([user, building, reference])
    session.flush()
    reference.object_type = ObjectType.BUILDING
    assert reference.object is building
    reference.object_type = None
    assert reference.object is None


def test_changing_hybrid_identity_invalidates_target(hybrid_models):
    session, Event, User, _ = hybrid_models
    first, second = User(id=1), User(id=2)
    reference = Event(id=1, object_type=ObjectType.USER, object=first)
    session.add_all([first, second, reference])
    session.flush()
    reference.object_id = second.id
    assert reference.object is second


def test_hybrid_queries(hybrid_models):
    session, Event, User, Building = hybrid_models
    user, building = User(id=1), Building(id=1)
    first = Event(id=1, object_type=ObjectType.USER, object=user)
    second = Event(id=2, object_type=ObjectType.BUILDING, object=building)
    session.add_all([user, building, first, second])
    session.commit()
    alias = aliased(Event)
    for model in (Event, alias):
        assert session.scalars(sa.select(model).where(model.object == user)).all() == [first]
        assert session.scalars(sa.select(model).where(model.object != user)).all() == [second]
        assert session.scalars(sa.select(model).where(model.object.is_type(Building))).all() == [second]


@pytest.mark.parametrize("object_type, object_id", [(None, 1), (ObjectType.USER, None), (ObjectType.USER, 99)])
def test_unresolved_hybrid_relationship(hybrid_models, object_type, object_id):
    session, Event, _, _ = hybrid_models
    reference = Event(id=1, object_type=object_type, object_id=object_id)
    assert reference.object is None
    session.add(reference)
    session.commit()
    assert reference.object is None


def test_detached_hybrid_assignment(hybrid_models):
    session, Event, User, _ = hybrid_models
    first, second = User(id=1), User(id=2)
    reference = Event(id=1, object_type=ObjectType.USER, object=first)
    session.add_all([first, second, reference])
    session.flush()
    session.expunge_all()
    reference.object = second
    assert reference.object is second
    session.add(reference)
    session.commit()
    assert reference.object.id == 2


def test_hybrid_reassignment_to_different_model(hybrid_models):
    session, Event, User, Building = hybrid_models
    user, building = User(id=1), Building(id=1)
    reference = Event(id=1, object_type=ObjectType.USER, object=user)
    session.add_all([user, building, reference])
    session.commit()
    reference.object = building
    reference.object_type = ObjectType.BUILDING
    assert reference.object is building
    session.commit()
    session.expunge_all()
    assert isinstance(session.get(Event, 1).object, Building)


def test_hybrid_deleted_target_is_not_returned_from_cache(hybrid_models):
    session, Event, User, _ = hybrid_models
    target = User(id=1)
    reference = Event(id=1, object_type=ObjectType.USER, object=target)
    session.add_all([target, reference])
    session.flush()
    session.delete(target)
    session.flush()
    assert reference.object is None
    session.commit()
    assert reference.object is None


def test_writable_hybrid_discriminator(engine):
    class Base(DeclarativeBase):
        pass

    class Node(Base):
        __tablename__ = "generic_writable_node"
        id = mapped_column(sa.Integer, primary_key=True)
        parent_id = mapped_column(sa.Integer)
        parent_kind = mapped_column(sa.String(30))

        @hybrid_property
        def parent_type(self):
            return self.parent_kind

        @parent_type.setter
        def parent_type(self, value):
            self.parent_kind = value

        parent = generic_relationship(parent_type, parent_id)

    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            parent = Node(id=1)
            child = Node(id=2, parent=parent)
            assert child.parent is parent
            assert child.parent_kind == "Node"
            session.add_all([parent, child])
            session.commit()
            assert child.parent is parent
            child.parent = None
            session.commit()
            assert child.parent is None
            assert child.parent_kind is None
            assert child.parent_id is None
    finally:
        Base.metadata.drop_all(engine)
        Base.registry.dispose()
