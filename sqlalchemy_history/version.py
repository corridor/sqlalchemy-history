import functools
import typing as t

import sqlalchemy as sa
import typing_extensions as te

from sqlalchemy_history.reverter import Reverter
from sqlalchemy_history.utils import get_versioning_manager, is_internal_column, parent_class


class VersionClassBase:
    @functools.cached_property
    def previous(self) -> t.Optional[te.Self]:
        """Returns the previous version relative to this version in the version
        history. If current version is the first version this method returns
        None.


        """
        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).previous(self)

    @functools.cached_property
    def next(self) -> t.Optional[te.Self]:
        """Returns the next version relative to this version in the version
        history. If current version is the last version this method returns
        None.


        """

        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).next(self)

    @functools.cached_property
    def index(self) -> t.Optional[int]:
        """ """
        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).index(self)

    @property
    def changeset(self) -> dict[str, list[t.Any]]:
        """
        Return a dictionary of changed fields in this version with keys as
        field names and values as lists with first value as the old field value
        and second list value as the new value.

        """
        previous_version = self.previous
        data = {}

        for key in sa.inspect(self.__class__).columns.keys():  # noqa: SIM118
            if is_internal_column(self, key):
                continue
            old = None if not previous_version else getattr(previous_version, key)
            new = getattr(self, key)
            if old != new:
                data[key] = [old, new]

        manager = get_versioning_manager(self)
        manager.plugins.after_construct_changeset(self, data)
        return data

    def revert(self, relations: t.Optional[t.Sequence[str]] = None) -> t.Any:
        if relations is None:
            relations = []
        return Reverter(self, relations=relations)()
