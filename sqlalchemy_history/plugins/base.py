class Plugin:
    def is_session_modified(self, session) -> bool:
        return False

    def after_build_tx_class(self, manager) -> None:
        pass

    def after_build_models(self, manager) -> None:
        pass

    def after_build_version_table_columns(self, table_builder, columns) -> None:
        pass

    def before_flush(self, uow, session) -> None:
        pass

    def before_create_version_objects(self, uow, session) -> None:
        pass

    def after_create_version_objects(self, uow, session) -> None:
        pass

    def after_create_version_object(self, uow, parent_obj, version_obj) -> None:
        pass

    def transaction_args(self, uow, session):
        return {}

    def after_version_class_built(self, parent_cls, version_cls) -> None:
        pass

    def after_construct_changeset(self, version_obj, changeset) -> None:
        pass


class PluginCollection:
    def __init__(self, plugins=None) -> None:
        if plugins is None:
            plugins = []
        if isinstance(plugins, self.__class__):
            self.plugins = plugins.plugins
        else:
            self.plugins = plugins

    def __iter__(self):
        yield from self.plugins

    def __len__(self) -> int:
        return len(self.plugins)

    def __repr__(self) -> str:
        return "<{} [{}]>".format(
            self.__class__.__name__,
            ", ".join(map(repr, self.plugins)),
        )

    def __getitem__(self, index):
        return self.plugins[index]

    def __setitem__(self, index, element) -> None:
        self.plugins[index] = element

    def __delitem__(self, index) -> None:
        del self.plugins[index]

    def __getattr__(self, attr):
        def wrapper(*args, **kwargs):
            return [getattr(plugin, attr)(*args, **kwargs) for plugin in self.plugins]

        return wrapper

    def append(self, el) -> None:
        self.plugins.append(el)
