from __future__ import annotations


class VersioningError(Exception):
    pass


class ClassNotVersioned(VersioningError):  # noqa: N818
    pass


class TableNotVersioned(VersioningError):  # noqa: N818
    pass


class ImproperlyConfigured(VersioningError):  # noqa: N818
    pass


class NoChangesAttribute(Exception):  # noqa: N818
    pass
