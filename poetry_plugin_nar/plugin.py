# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_plugin_nar.command import BuildCommand


if TYPE_CHECKING:
    from poetry.console.application import Application
    from poetry.console.commands.command import Command


class BuildPlugin(ApplicationPlugin):
    @property
    def commands(self) -> list[type[Command]]:
        return [BuildCommand]

    def activate(self, application: Application) -> None:
        # Removing the existing build command to avoid an error

        # If you're checking this code out to get inspiration
        # for your own plugins: DON'T DO THIS!
        if application.command_loader.has("build"):
            del application.command_loader._factories["build"]

        super().activate(application=application)
