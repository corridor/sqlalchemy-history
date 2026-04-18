import typing as t


class Plugin:
    def is_session_modified(self, session: t.Any) -> bool:
        return False

    def after_build_tx_class(self, manager: t.Any) -> None:
        pass

    def after_build_models(self, manager: t.Any) -> None:
        pass

    def after_build_version_table_columns(self, table_builder: t.Any, columns: list[t.Any]) -> None:
        pass

    def before_flush(self, uow: t.Any, session: t.Any) -> None:
        pass

    def before_create_version_objects(self, uow: t.Any, session: t.Any) -> None:
        pass

    def after_create_version_objects(self, uow: t.Any, session: t.Any) -> None:
        pass

    def after_create_version_object(self, uow: t.Any, parent_obj: t.Any, version_obj: t.Any) -> None:
        pass

    def transaction_args(self, uow: t.Any, session: t.Any) -> dict[str, t.Any]:
        return {}

    def after_version_class_built(self, parent_cls: type[t.Any], version_cls: type[t.Any]) -> None:
        pass

    def after_construct_changeset(self, version_obj: t.Any, changeset: dict[str, list[t.Any]]) -> None:
        pass


class PluginCollection:
    def __init__(self, plugins: t.Optional[t.Union["PluginCollection", t.Sequence[Plugin]]] = None) -> None:
        if plugins is None:
            plugins = []
        if isinstance(plugins, self.__class__):
            self.plugins = plugins.plugins
        else:
            self.plugins = list(plugins)

    def __iter__(self) -> t.Iterator[Plugin]:
        yield from self.plugins

    def __len__(self) -> int:
        return len(self.plugins)

    def __repr__(self) -> str:
        return "<{} [{}]>".format(
            self.__class__.__name__,
            ", ".join(map(repr, self.plugins)),
        )

    def __getitem__(self, index: int) -> Plugin:
        return self.plugins[index]

    def __setitem__(self, index: int, element: Plugin) -> None:
        self.plugins[index] = element

    def __delitem__(self, index: int) -> None:
        del self.plugins[index]

    def __getattr__(self, attr: str) -> t.Callable[..., list[t.Any]]:
        def wrapper(*args: t.Any, **kwargs: t.Any) -> list[t.Any]:
            return [getattr(plugin, attr)(*args, **kwargs) for plugin in self.plugins]

        return wrapper

    def append(self, el: Plugin) -> None:
        self.plugins.append(el)
