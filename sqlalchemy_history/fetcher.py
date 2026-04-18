"""Fetcher Module helps traverse across versions for a given versioned object."""

import operator
import typing as t

import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy_utils import get_primary_keys, identity

from sqlalchemy_history.utils import end_tx_column_name, tx_column_name


if t.TYPE_CHECKING:
    from sqlalchemy_history.manager import VersioningManager

_T = t.TypeVar("_T", bound=sa.orm.DeclarativeBase)


def parent_identity(obj_or_class: object) -> tuple[t.Any, ...]:
    return tuple(
        getattr(obj_or_class, column_key)
        for column_key in get_primary_keys(obj_or_class)
        if column_key != tx_column_name(obj_or_class)
    )


def eqmap(
    callback: t.Callable[..., tuple[t.Any, ...]],
    iterable: t.Iterable[t.Any],
) -> t.Iterator[sa.ColumnElement[bool]]:
    for a, b in zip(*map(callback, iterable)):
        yield a == b


def parent_criteria(obj: _T, class_: t.Optional[type] = None) -> t.Iterator[sa.ColumnElement[bool]]:
    if class_ is None:
        class_ = obj.__class__
    return eqmap(parent_identity, (class_, obj))


class VersionObjectFetcher(t.Generic[_T]):
    def __init__(self, manager: "VersioningManager") -> None:
        self.manager = manager

    def previous_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        raise NotImplementedError

    def next_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        raise NotImplementedError

    def previous(self, obj: _T) -> t.Optional[_T]:
        """
        Returns the previous version relative to this version in the version
        history. If current version is the first version this method returns
        None.
        """
        session = sa.orm.object_session(obj)
        if session is None:
            raise sa.orm.exc.DetachedInstanceError(f"Instance {obj!r} is not bound to any session")
        return session.scalars(self.previous_query(obj).limit(1)).first()

    def index(self, obj: _T) -> t.Optional[int]:
        """
        Return the index of this version in the version history.
        """
        session = sa.orm.object_session(obj)
        if session is None:
            raise sa.orm.exc.DetachedInstanceError(f"Instance {obj!r} is not bound to any session")
        return session.scalar(self._index_query(obj))

    def next(self, obj: _T) -> t.Optional[_T]:
        """
        Returns the next version relative to this version in the version
        history. If current version is the last version this method returns
        None.
        """
        session = sa.orm.object_session(obj)
        if session is None:
            raise sa.orm.exc.DetachedInstanceError(f"Instance {obj!r} is not bound to any session")
        return session.scalars(self.next_query(obj).limit(1)).first()

    def _transaction_id_subquery(
        self,
        obj: _T,
        next_or_prev: t.Literal["next", "previous"] = "next",
        alias: t.Any = None,  # noqa: ANN401
    ) -> sa.Select[tuple[int]]:
        if next_or_prev == "next":
            op = operator.gt
            func = sa.func.min
        else:
            op = operator.lt
            func = sa.func.max

        if alias is None:
            alias = sa.orm.aliased(obj.__class__)
            table = alias.__table__
            attrs = alias.c if hasattr(alias, "c") else alias
        else:
            table = alias.original
            attrs = alias.c
        query = (
            sa.select(func(getattr(attrs, tx_column_name(obj))))
            .select_from(table)
            .where(
                sa.and_(
                    op(
                        getattr(attrs, tx_column_name(obj)),
                        getattr(obj, tx_column_name(obj)),
                    ),
                    *[
                        getattr(attrs, pk) == getattr(obj, pk)
                        for pk in get_primary_keys(obj.__class__)
                        if pk != tx_column_name(obj)
                    ],
                )
            )
            .correlate(table)
        )
        return query.scalar_subquery()

    def _next_prev_query(
        self,
        obj: _T,
        next_or_prev: t.Literal["next", "previous"] = "next",
    ) -> sa.Select[tuple[_T]]:
        subquery = self._transaction_id_subquery(obj, next_or_prev=next_or_prev)
        subquery = subquery.scalar_subquery()

        return sa.select(obj.__class__).filter(
            sa.and_(getattr(obj.__class__, tx_column_name(obj)) == subquery, *parent_criteria(obj))
        )

    def _index_query(self, obj: _T) -> sa.Select[tuple[int]]:
        """
        Returns the query needed for fetching the index of this record relative
        to version history.
        """
        alias = sa.orm.aliased(obj.__class__)

        subquery = (
            sa.select(sa.func.count(sa.literal("1")))
            .select_from(alias.__table__)
            .where(getattr(alias, tx_column_name(obj)) < getattr(obj, tx_column_name(obj)))
            .correlate(alias.__table__)
            .label("position")
        )
        return (
            sa.select(subquery)
            .select_from(obj.__table__)
            .where(sa.and_(*eqmap(identity, (obj.__class__, obj))))
            .order_by(getattr(obj.__class__, tx_column_name(obj)))
        )


class SubqueryFetcher(VersionObjectFetcher):
    def previous_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        """
        Returns the query that fetches the previous version relative to this
        version in the version history.
        """
        return self._next_prev_query(obj, "previous")

    def next_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        """
        Returns the query that fetches the next version relative to this
        version in the version history.
        """
        return self._next_prev_query(obj, "next")


class ValidityFetcher(VersionObjectFetcher):
    def next_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        """
        Returns the query that fetches the next version relative to this
        version in the version history.
        """
        return sa.select(obj.__class__).filter(
            sa.and_(
                getattr(obj.__class__, tx_column_name(obj)) == getattr(obj, end_tx_column_name(obj)),
                *parent_criteria(obj),
            )
        )

    def previous_query(self, obj: _T) -> sa.Select[tuple[_T]]:
        """
        Returns the query that fetches the previous version relative to this
        version in the version history.
        """
        return sa.select(obj.__class__).filter(
            sa.and_(
                getattr(obj.__class__, end_tx_column_name(obj)) == getattr(obj, tx_column_name(obj)),
                *parent_criteria(obj),
            )
        )
