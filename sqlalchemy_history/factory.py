"""
Factory package manages and makes sure if a model class already exists indeclarative model registry or not
"""

from __future__ import annotations

import typing as t


if t.TYPE_CHECKING:
    from sqlalchemy_history.manager import VersioningManager


class ModelFactory:
    model_name = None

    def __call__(self, manager: VersioningManager) -> t.Any:  # noqa: ANN401
        """Create model class but only if it doesn't already exist
        in declarative model registry.
        """
        Base = manager.declarative_base  # noqa: N806 -- Base is a class
        registry = Base.registry._class_registry

        if self.model_name not in registry:
            return self.create_class(manager)
        return registry[self.model_name]
