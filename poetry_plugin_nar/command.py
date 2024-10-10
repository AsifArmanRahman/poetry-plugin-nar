# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

from poetry.console.commands.build import BuildCommand as BaseBuildCommand

from poetry_plugin_nar.nar import NarBuilder


if TYPE_CHECKING:
    from pathlib import Path


class BuildCommand(BaseBuildCommand):
    def _build(
        self,
        fmt: str,
        executable: str | Path | None = None,
        *,
        target_dir: Path | None = None,
    ) -> None:
        from poetry.masonry.builders import BUILD_FORMATS

        if fmt in BUILD_FORMATS:
            builders = [BUILD_FORMATS[fmt]]
        elif fmt == "nar":
            builders = [NarBuilder]
        elif fmt == "all":
            builders = list(BUILD_FORMATS.values())
        else:
            raise ValueError(f"Invalid format: {fmt}")

        for builder in builders:
            builder(self.poetry, executable=executable).build(target_dir)
