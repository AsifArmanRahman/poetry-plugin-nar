# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import os
import shutil
import tempfile

from datetime import datetime
from datetime import timezone
from pathlib import Path
from subprocess import PIPE
from subprocess import check_call
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from poetry.core.masonry.builders.builder import Builder
from poetry.core.masonry.builders.builder import BuildIncludeFile
from poetry.core.masonry.builders.wheel import WheelBuilder
from poetry.core.masonry.utils.helpers import distribution_name
from poetry.core.masonry.utils.helpers import normalize_file_permissions
from poetry.core.utils.helpers import temporary_directory


if TYPE_CHECKING:
    from collections.abc import Iterable

# as builders have their own logging format, and can't be extended
# as of now, we set the logger for NarBuilder to the same as Builder
# so that the logs are consistent with the rest of the build process
logger = logging.getLogger("poetry.core.masonry.builders.builder")


MANIFEST_BASE = """\
Manifest-Version: 1.0
Created-By: poetry-plugin-nar
Build-Timestamp: {timestamp}
Nar-Id: {name}-nar
Nar-Group: {name}
Nar-Version: {version}
"""


class NarBuilder(Builder):
    format = "nar"

    @property
    def filename(self) -> str:
        name = distribution_name(self._package.name)
        return f"{name}-{self._package.version}.nar"

    def build(self, target_dir: Path | None = None) -> Path:
        logger.info(f"Building {self.format}")

        # if target_dir is not provided, use the default target dir
        target_dir = target_dir or self.default_target_dir

        # if the target_dir does not exist, create it
        if not target_dir.exists():
            target_dir.mkdir(parents=True)

        # target file path
        target = target_dir / self.filename

        # if the target file already exists, remove it
        if target.exists():
            target.unlink()

        # Create a temporary nar file
        fd, temp_file_path = tempfile.mkstemp(suffix=".nar")

        # Normalize permission bits in accord with poetry WheelBuilder
        st_mode = os.stat(temp_file_path).st_mode
        new_mode = normalize_file_permissions(st_mode)
        os.chmod(temp_file_path, new_mode)

        with (
            os.fdopen(fd, "w+b") as fd_file,
            ZipFile(fd_file, mode="w", compression=ZIP_DEFLATED) as zip_file,
        ):
            # Copy the mentioned package/s to the nar file
            self._copy_module(zip_file)

            with temporary_directory() as temp_dir:
                self._prepare_metadata(Path(temp_dir))
                self._copy_folder(zip_file, Path(temp_dir), "META-INF")

            with temporary_directory() as temp_dir:
                self._prepare_dependencies(target_dir, Path(temp_dir))
                self._copy_folder(
                    zip_file, Path(temp_dir), "NAR-INF/bundled-dependencies"
                )

        # rename and move the temporary nar file to the target file path
        shutil.move(temp_file_path, target.as_posix())

        logger.info(f"Built <comment>{self.filename}</comment>")
        return target

    def _copy_module(self, nar: ZipFile) -> None:
        WheelBuilder(poetry=self._poetry)._copy_module(nar)

    def _prepare_metadata(self, metadata_dir: Path) -> None:
        # Copy the legal files
        for legal_file in self._get_legal_files():
            if not legal_file.is_file():
                logger.debug(f"Skipping: {legal_file.as_posix()}")
                continue

            dest = metadata_dir / legal_file.relative_to(self._path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(legal_file, dest)

        # Copy readme file/s if mentioned in pyproject.toml
        if "readme" in self._poetry.local_config:
            readme: str | Iterable[str] = self._poetry.local_config["readme"]

            if isinstance(readme, str):
                file = BuildIncludeFile(
                    path=readme,
                    project_root=self._path,
                    source_root=self._path,
                )
                shutil.copy(file.path, metadata_dir / Path(readme).name)
            else:
                for r in readme:
                    file = BuildIncludeFile(
                        path=r,
                        project_root=self._path,
                        source_root=self._path,
                    )
                    shutil.copy(file.path, metadata_dir / Path(r).name)

        # Write the MANIFEST.MF file
        with open(
            f"{metadata_dir}/MANIFEST.MF", "w", encoding="utf-8", newline="\n"
        ) as f:
            f.write(
                MANIFEST_BASE.format(
                    timestamp=datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    name=self._meta.name,
                    version=self._meta.version,
                )
            )

    def _copy_folder(self, nar: ZipFile, source: Path, target: str) -> None:
        for file in sorted(source.glob("**/*")):
            if not file.is_file():
                continue

            rel_path = file.relative_to(source)
            target_path = target / rel_path
            self._add_file(nar, file, target_path)

    def _prepare_dependencies(self, cache: Path, deps_dir: Path) -> None:
        # Create a temporary requirements.txt file
        _, temp_file_path = tempfile.mkstemp(suffix=".txt")

        # command to export the requirements to a requirements.txt file
        command = [
            "poetry",
            "export",
            "-f",
            "requirements.txt",
            "--output",
            Path(temp_file_path).as_posix(),
        ]

        self._execute_command(command)

        # directory to store the pip cache
        cache_dir = cache / "pip-cache"

        # if the cache directory does not exist, create it
        if not cache_dir.exists():
            cache_dir.mkdir()

        # command to download the dependencies
        # to the dependency unpack directory
        command = [
            self.executable.absolute().as_posix(),
            "-m",
            "pip",
            "install",
            "-r",
            f"{Path(temp_file_path).absolute().as_posix()}",
            "--upgrade",
            "--no-python-version-warning",
            "--no-input",
            "--cache-dir",
            cache_dir.absolute().as_posix(),
            "--quiet",
            "--target",
            deps_dir.absolute().as_posix(),
        ]

        self._execute_command(command)

    def _execute_command(self, command: list[str]) -> None:
        # run the command to export the requirements
        check_call(command, stdout=PIPE, stderr=PIPE, cwd=self._path)

    def _add_file(
        self, nar: ZipFile, full_path: Path, rel_path: Path
    ) -> None:
        WheelBuilder(poetry=self._poetry)._add_file(nar, full_path, rel_path)
