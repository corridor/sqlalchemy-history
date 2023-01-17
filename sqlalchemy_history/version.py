import sqlalchemy as sa
from cached_property import cached_property

from sqlalchemy_history.reverter import Reverter
from sqlalchemy_history.utils import (
    get_versioning_manager,
    is_internal_column,
    parent_class,
)


class VersionClassBase(object):
    @cached_property
    def previous(self):
        """Returns the previous version relative to this version in the version
        history. If current version is the first version this method returns
        None.


        """
        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).previous(self)

    @cached_property
    def next(self):
        """Returns the next version relative to this version in the version
        history. If current version is the last version this method returns
        None.


        """
        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).next(self)

    @cached_property
    def index(self):
        """ """
        return get_versioning_manager(self).fetcher(parent_class(self.__class__)).index(self)

    @property
    def changeset(self):
        """
        Return a dictionary of changed fields in this version with keys as
        field names and values as lists with first value as the old field value
        and second list value as the new value.

        """
        previous_version = self.previous
        data = {}

        for key in sa.inspect(self.__class__).columns.keys():
            if is_internal_column(self, key):
                continue
            if not previous_version:
                old = None
            else:
                old = getattr(previous_version, key)
            new = getattr(self, key)
            if old != new:
                data[key] = [old, new]

        manager = get_versioning_manager(self)
        manager.plugins.after_construct_changeset(self, data)
        return data

    def revert(self, relations=[]):
        return Reverter(self, relations=relations)()
