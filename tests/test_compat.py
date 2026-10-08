import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import oracle, postgresql, sqlite
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Session, aliased

from sqlalchemy_history._compat.sqlalchemy_utils import (
    JSONType,
    generic_relationship,
    get_columns,
    get_hybrid_properties,
    get_primary_keys,
    identity,
)
from sqlalchemy_history.utils import ordered_sequence


@pytest.fixture
def models():
    class Base(DeclarativeBase):
        pass

    class Target(Base):
        __tablename__ = "compat_target"
        tenant = sa.Column(sa.Integer, primary_key=True)
        id = sa.Column("target_pk", sa.Integer, primary_key=True)
        kind = sa.Column(sa.String(30))
        __mapper_args__ = {"polymorphic_on": kind, "polymorphic_identity": "target"}

        @hybrid_property
        def doubled_id(self):
            return self.id * 2

    class Child(Target):
        __mapper_args__ = {"polymorphic_identity": "child"}

    class Grandchild(Child):
        __mapper_args__ = {"polymorphic_identity": "grandchild"}

    class Reference(Base):
        __tablename__ = "compat_reference"
        id = sa.Column(sa.Integer, primary_key=True)
        kind = sa.Column("target_kind", sa.String(30))
        tenant = sa.Column(sa.Integer)
        target_id = sa.Column("target_pk", sa.Integer)
        target = generic_relationship(kind, (tenant, target_id))
        by_name = generic_relationship("kind", ("tenant", "target_id"))

    Reference.by_attribute = generic_relationship(Reference.kind, (Reference.tenant, Reference.target_id))
    yield Base, Target, Child, Grandchild, Reference
    Base.registry.dispose()


@pytest.fixture
def compat_session(models, engine):
    Base = models[0]
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_identity_and_hybrids_use_mapped_attribute_names(models):
    _, Target, _, _, _ = models
    target = Target(tenant=4, id=7)
    assert identity(target) == (4, 7)
    assert tuple(get_primary_keys(Target)) == ("tenant", "id")
    for model in (Target, target, sa.inspect(Target), aliased(Target)):
        assert tuple(get_hybrid_properties(model)) == ("doubled_id",)


def test_select_columns_keep_original_columns(models):
    Target = models[1]
    statement = sa.select(Target.id, Target.tenant)
    assert get_columns(statement).id.table is Target.__table__
    assert get_columns(statement).id.name == "target_pk"
    assert tuple(get_primary_keys(statement)) == ("id", "tenant")


@pytest.mark.parametrize("attribute", ["target", "by_name", "by_attribute"])
def test_generic_relationship_assignment_and_reload(models, compat_session, attribute):
    _, Target, _, _, Reference = models
    target = Target(tenant=4, id=7)
    reference = Reference(id=1)
    setattr(reference, attribute, target)
    assert getattr(reference, attribute) is target
    assert (reference.kind, reference.tenant, reference.target_id) == ("Target", 4, 7)
    compat_session.add_all([target, reference])
    compat_session.commit()
    assert getattr(reference, attribute) is target
    setattr(reference, attribute, None)
    compat_session.commit()
    assert getattr(reference, attribute) is None
    assert (reference.kind, reference.tenant, reference.target_id) == (None, None, None)


def test_generic_relationship_reassignment_is_persisted(models, compat_session):
    _, Target, _, _, Reference = models
    first = Target(tenant=4, id=7)
    second = Target(tenant=4, id=8)
    reference = Reference(id=1, target=first)
    compat_session.add_all([first, second, reference])
    compat_session.commit()
    reference.target = second
    compat_session.commit()
    assert reference.target is second
    reference.target = first
    compat_session.rollback()
    assert reference.target is second


def test_generic_relationship_expiration_invalidates_cached_target(models, compat_session):
    _, Target, _, _, Reference = models
    target = Target(tenant=4, id=7)
    reference = Reference(id=1, target=target)
    compat_session.add_all([target, reference])
    compat_session.flush()
    assert reference.target is target
    compat_session.delete(target)
    compat_session.commit()
    assert reference.target is None


def test_generic_relationship_expiration_reloads_detached_target(models, compat_session):
    _, Target, _, _, Reference = models
    target = Target(tenant=4, id=7)
    reference = Reference(id=1, target=target)
    compat_session.add_all([target, reference])
    compat_session.flush()
    compat_session.expunge(target)
    compat_session.expire(reference)
    reloaded = reference.target
    assert reloaded is not target
    assert identity(reloaded) == (4, 7)
    assert sa.inspect(reloaded).session is compat_session


def test_generic_relationship_direct_keys_override_cached_target(models, compat_session):
    _, Target, _, _, Reference = models
    first = Target(tenant=4, id=7)
    second = Target(tenant=4, id=8)
    reference = Reference(id=1, target=first)
    compat_session.add_all([first, second, reference])
    compat_session.flush()
    reference.target_id = second.id
    assert reference.target is second
    reference.kind = "Unknown"
    assert reference.target is None


def test_generic_relationship_queries_support_aliases_and_descendants(models, compat_session):
    _, Target, Child, Grandchild, Reference = models
    first = Target(tenant=4, id=7)
    second = Grandchild(tenant=4, id=8)
    reference = Reference(id=1, target=first)
    descendant_reference = Reference(id=2, target=second)
    compat_session.add_all([first, second, reference, descendant_reference])
    compat_session.commit()
    alias = aliased(Reference)
    assert compat_session.scalars(sa.select(alias).where(alias.target == first)).all() == [reference]
    assert compat_session.scalars(sa.select(alias).where(alias.target != first)).all() == [descendant_reference]
    assert compat_session.scalars(sa.select(alias).where(alias.target.is_type(Child))).all() == [descendant_reference]


def test_generic_relationship_null_identity_does_not_warn(models, compat_session):
    Reference = models[-1]
    reference = Reference(id=1, kind="Target")
    compat_session.add(reference)
    compat_session.commit()
    assert reference.target is None


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect(), oracle.dialect()])
@pytest.mark.parametrize("value", [None, {"nested": [1, "two", True]}])
def test_json_type_roundtrip(dialect, value):
    type_ = JSONType().dialect_impl(dialect)
    bound = type_.process_bind_param(value, dialect)
    assert type_.process_result_value(bound, dialect) == value


def test_ordered_sequence_preserves_oracle_ordering():
    ddl = str(sa.schema.CreateSequence(ordered_sequence("compat_seq")).compile(dialect=oracle.dialect()))
    assert "START WITH 1" in ddl
    assert "ORDER" in ddl
