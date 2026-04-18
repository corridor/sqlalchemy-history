"""Operations module contains Operation Class."""

import typing as t
from collections import OrderedDict
from copy import copy

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy_utils import identity


class Operation:
    INSERT = 0
    UPDATE = 1
    DELETE = 2

    def __init__(self, target: DeclarativeBase, type_: int) -> None:
        self.target = target
        self.type = type_
        self.processed = False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Operation):
            return False
        return self.target == other.target and self.type == other.type

    def __ne__(self, other: object) -> bool:
        return not (self == other)


class Operations:
    """A collection of operations"""

    def __init__(self) -> None:
        self.objects: OrderedDict[tuple[type[t.Any], t.Any], Operation] = OrderedDict()

    def format_key(self, target: object) -> tuple[type[t.Any], t.Any]:
        # We cannot use target._sa_instance_state.identity here since object's
        # identity is not yet updated at this phase
        return (target.__class__, identity(target))

    def __contains__(self, target: object) -> bool:
        return self.format_key(target) in self.objects

    def __setitem__(self, key: tuple[type[t.Any], t.Any], operation: Operation) -> None:
        self.objects[key] = operation

    def __getitem__(self, key: tuple[type[t.Any], t.Any]) -> Operation:
        return self.objects[key]

    def __delitem__(self, key: tuple[type[t.Any], t.Any]) -> None:
        del self.objects[key]

    def __bool__(self) -> bool:
        return bool(self.objects)

    def __nonzero__(self) -> bool:
        return self.__bool__()

    def __repr__(self) -> str:
        return repr(self.objects)

    @property
    def entities(self) -> set[type[t.Any]]:
        """Return a set of changed versioned entities for given session.

        :param session: SQLAlchemy session object
        """
        return {key[0] for key, _ in self.items()}

    def items(self) -> t.ItemsView[tuple[type[t.Any], t.Any], Operation]:
        return self.objects.items()

    def add(self, operation: Operation) -> None:
        self[self.format_key(operation.target)] = operation

    def add_insert(self, target: DeclarativeBase) -> None:
        if target in self:
            # If the object is deleted and then inserted within the same
            # transaction we are actually dealing with an update.
            self.add(Operation(target, Operation.UPDATE))
        else:
            self.add(Operation(target, Operation.INSERT))

    def add_update(self, target: DeclarativeBase) -> None:
        state_copy = copy(sa.inspect(target).committed_state)
        relationships = sa.inspect(target.__class__).relationships
        # Remove all ONETOMANY and MANYTOMANY relationships
        for rel_key, relationship in relationships.items():
            if relationship.direction.name in ["ONETOMANY", "MANYTOMANY"] and rel_key in state_copy:
                del state_copy[rel_key]

        if state_copy:
            if target in self:
                # If already in current transaction and some event hook did a update
                # prior to commit hook, continue with operation type as it is
                self.add(Operation(target, self[self.format_key(target)].type))
            else:
                self.add(Operation(target, Operation.UPDATE))

    def add_delete(self, target: object) -> None:
        self.add(Operation(target, Operation.DELETE))
