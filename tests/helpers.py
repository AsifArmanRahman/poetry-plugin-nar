# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.config.config import Config as BaseConfig
from poetry.console.application import Application
from poetry.factory import Factory
from poetry.installation.executor import Executor


if TYPE_CHECKING:
    from typing import Any

    from poetry.core.packages.package import Package
    from poetry.installation.operations.operation import Operation
    from poetry.poetry import Poetry


class Config(BaseConfig):
    def get(self, setting_name: str, default: Any = None) -> Any:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().get(setting_name, default=default)

    def raw(self) -> dict[str, Any]:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().raw()

    def all(self) -> dict[str, Any]:
        self.merge(self._config_source.config)  # type: ignore[attr-defined]
        self.merge(self._auth_config_source.config)  # type: ignore[attr-defined]

        return super().all()


class PoetryTestApplication(Application):
    def __init__(self, poetry: Poetry) -> None:
        super().__init__()
        self._poetry = poetry

    def reset_poetry(self) -> None:
        poetry = self._poetry
        assert poetry
        self._poetry = Factory().create_poetry(poetry.file.path.parent)
        self._poetry.set_pool(poetry.pool)
        self._poetry.set_config(poetry.config)


class TestExecutor(Executor):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self._installs: list[Package] = []
        self._updates: list[Package] = []
        self._uninstalls: list[Package] = []

    @property
    def installations(self) -> list[Package]:
        return self._installs

    @property
    def updates(self) -> list[Package]:
        return self._updates

    @property
    def removals(self) -> list[Package]:
        return self._uninstalls

    def _do_execute_operation(self, operation: Operation) -> int:
        rc = super()._do_execute_operation(operation)

        if not operation.skipped:
            getattr(self, f"_{operation.job_type}s").append(operation.package)

        return rc

    def _execute_install(self, operation: Operation) -> int:
        return 0

    def _execute_update(self, operation: Operation) -> int:
        return 0

    def _execute_remove(self, operation: Operation) -> int:
        return 0
