"""
Factory package manages and makes sure if a model class already exists indeclarative model registry or not
"""

import typing as t

from sqlalchemy.orm.clsregistry import ClsRegistryToken


if t.TYPE_CHECKING:
    from sqlalchemy_history.manager import VersioningManager


class ModelFactory:
    model_name: t.ClassVar[str]

    def create_class(self, manager: "VersioningManager") -> type:
        raise NotImplementedError

    def __call__(self, manager: "VersioningManager") -> t.Union[type, ClsRegistryToken]:
        """Create model class but only if it doesn't already exist
        in declarative model registry.
        """
        Base = manager.declarative_base  # noqa: N806
        registry = Base.registry._class_registry

        if self.model_name not in registry:
            return self.create_class(manager)
        return registry[self.model_name]
