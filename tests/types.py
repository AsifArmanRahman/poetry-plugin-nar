# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol


if TYPE_CHECKING:
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from poetry.installation import Installer
    from poetry.installation.executor import Executor
    from poetry.poetry import Poetry
    from poetry.utils.env import Env


class FixtureDirGetter(Protocol):
    def __call__(self, name: str) -> Path: ...


class ProjectFactory(Protocol):
    def __call__(self, source: Path) -> Poetry: ...


class CommandTesterFactory(Protocol):
    def __call__(
        self,
        command: str,
        poetry: Poetry | None = None,
        installer: Installer | None = None,
        executor: Executor | None = None,
        environment: Env | None = None,
    ) -> CommandTester: ...
