from __future__ import annotations

import typing as t


if t.TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from sqlalchemy_history.manager import VersioningManager
    from sqlalchemy_history.unit_of_work import UnitOfWork


class Plugin:
    def is_session_modified(self, session: Session) -> bool:
        return False

    def after_build_tx_class(self, manager: VersioningManager):
        pass

    def after_build_models(self, manager: VersioningManager):
        pass

    def after_build_version_table_columns(self, table_builder, columns):
        pass

    def before_flush(self, uow, session: Session):
        pass

    def before_create_version_objects(self, uow: UnitOfWork, session: Session):
        pass

    def after_create_version_objects(self, uow: UnitOfWork, session: Session):
        pass

    def after_create_version_object(self, uow: UnitOfWork, parent_obj, version_obj):
        pass

    def transaction_args(self, uow: UnitOfWork, session: Session):
        return {}

    def after_version_class_built(self, parent_cls, version_cls):
        pass

    def after_construct_changeset(self, version_obj, changeset):
        pass


class PluginCollection:
    plugins: list[type[Plugin]]

    def __init__(self, plugins: list[type[Plugin]] | PluginCollection | None = None) -> None:
        if plugins is None:
            plugins = []
        if isinstance(plugins, PluginCollection):
            self.plugins = plugins.plugins
        else:
            self.plugins = plugins

    def __iter__(self) -> t.Generator[type[Plugin], t.Any, None]:
        yield from self.plugins

    def __len__(self) -> int:
        return len(self.plugins)

    def __repr__(self) -> str:
        return "<{} [{}]>".format(
            self.__class__.__name__,
            ", ".join(map(repr, self.plugins)),
        )

    def __getitem__(self, index: int) -> type[Plugin]:
        return self.plugins[index]

    def __setitem__(self, index: int, element: type[Plugin]) -> None:
        self.plugins[index] = element

    def __delitem__(self, index: int) -> None:
        del self.plugins[index]

    def __getattr__(self, attr: str) -> t.Callable[..., t.Any]:
        def wrapper(*args, **kwargs) -> list[t.Any]:
            return [getattr(plugin, attr)(*args, **kwargs) for plugin in self.plugins]

        return wrapper

    def append(self, el: type[Plugin]) -> None:
        self.plugins.append(el)
