# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from cleo.io.null_io import NullIO
from poetry.console.commands.build import BuildCommand as BaseBuildCommand

from poetry_plugin_nar.command import BuildCommand


if TYPE_CHECKING:
    from tests.helpers import PoetryTestApplication


@pytest.mark.parametrize("project", ["simple-project"])
def test_plugin_override_build_command(app: PoetryTestApplication) -> None:
    app._load_plugins(NullIO())

    assert type(app.find("build")) is BuildCommand
    assert type(app.find("build")) is not BaseBuildCommand
