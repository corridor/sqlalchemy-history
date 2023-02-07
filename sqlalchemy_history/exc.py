class VersioningError(Exception):
    pass


class ClassNotVersioned(VersioningError):
    pass


class TableNotVersioned(VersioningError):
    pass


class ImproperlyConfigured(VersioningError):
    pass


class NoChangesAttribute(Exception):
    pass
