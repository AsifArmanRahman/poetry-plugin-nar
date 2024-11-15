# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import tempfile

from datetime import datetime
from datetime import timezone
from functools import cached_property
from pathlib import Path
from subprocess import PIPE
from subprocess import check_call
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo

import tomlkit

from poetry.core.masonry.builders.builder import Builder
from poetry.core.masonry.builders.builder import BuildIncludeFile
from poetry.core.masonry.utils.helpers import distribution_name
from poetry.core.masonry.utils.helpers import normalize_file_permissions
from poetry.core.utils.helpers import temporary_directory


if TYPE_CHECKING:
    from collections.abc import Iterable

    from poetry.core.masonry.utils.module import Module

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

    @cached_property
    def _module(self) -> Module:
        from poetry.core.masonry.utils.module import Module

        packages = []

        for p in self._package.packages:
            formats = p.get("format") or None

            # Default to "nar" format when `format` key is not
            # provided in the inline include table.
            if formats is None:
                formats = ["nar"]

            if not isinstance(formats, list):
                formats = [formats]

            if (
                formats
                and self.format
                and self.format not in formats
                and not self._ignore_packages_formats
            ):
                continue

            packages.append(p)

        includes = []
        for include in self._package.include:
            formats = include.get("format", [])

            if (
                formats
                and self.format
                and self.format not in formats
                and not self._ignore_packages_formats
            ):
                continue

            includes.append(include)

        return Module(
            self._package.name,
            self._path.as_posix(),
            packages=packages,
            includes=includes,
        )

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

        # Create a temporary nar file
        fd, tmp_file_path = tempfile.mkstemp(suffix=".nar")

        # Normalize permission bits in accord
        # with poetry WheelBuilder
        st_mode = os.stat(tmp_file_path).st_mode
        new_mode = normalize_file_permissions(st_mode)
        os.chmod(tmp_file_path, new_mode)

        with temporary_directory(prefix=self._package.name) as temp_dir:
            tmp_package_dir = Path(temp_dir)

            self._copy_module(tmp_package_dir)
            self._prepare_metadata(tmp_package_dir)

            if self._package.requires:
                self._prepare_dependencies(target_dir, tmp_package_dir)

            self._dynamic_metadata(tmp_package_dir)

            with (
                os.fdopen(fd, "w+b") as fd_file,
                ZipFile(
                    fd_file, mode="w", compression=ZIP_DEFLATED
                ) as zip_file,
            ):
                self._copy_folder(zip_file, tmp_package_dir)

        # target file path
        target = target_dir / self.filename

        # if the target file already exists, remove it
        if target.exists():
            target.unlink()

        # rename and move the temporary nar file to the target path
        shutil.move(tmp_file_path, target)

        logger.info(f"Built <comment>{self.filename}</comment>")
        return target

    def find_files_to_add(
        self, exclude_build: bool = True
    ) -> set[BuildIncludeFile]:
        """
        Finds all files to add to the nar package.
        """
        from poetry.core.masonry.utils.package_include import PackageInclude

        to_add = set()

        for include in self._module.includes:
            include.refresh()
            formats = include.formats or ["nar"]

            for file in include.elements:
                if "__pycache__" in str(file):
                    continue

                if (
                    isinstance(include, PackageInclude)
                    and include.source
                    and self.format == "nar"
                ):
                    source_root = include.base
                else:
                    source_root = self._path

                if (
                    isinstance(include, PackageInclude)
                    and include.target
                    and self.format == "nar"
                ):
                    target_dir = include.target
                else:
                    target_dir = None

                if file.is_dir():
                    if self.format in formats:
                        for current_file in file.glob("**/*"):
                            include_file = BuildIncludeFile(
                                path=current_file,
                                project_root=self._path,
                                source_root=source_root,
                                target_dir=target_dir,
                            )

                            if not (
                                current_file.is_dir()
                                or self.is_excluded(
                                    include_file.relative_to_source_root()
                                )
                            ):
                                to_add.add(include_file)
                    continue

                include_file = BuildIncludeFile(
                    path=file,
                    project_root=self._path,
                    source_root=source_root,
                    target_dir=target_dir,
                )

                if self.is_excluded(
                    include_file.relative_to_project_root()
                ) and isinstance(include, PackageInclude):
                    continue

                if file.suffix == ".pyc":
                    continue

                logger.debug(f"Adding: {file}")
                to_add.add(include_file)

        return to_add

    def _copy_module(self, nar_package_dir: Path) -> None:
        to_add = self.find_files_to_add()

        # sorting everything so the order is stable.
        for file in sorted(to_add, key=lambda x: x.path):
            dst = nar_package_dir / file.relative_to_target_root()
            dst.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(file.path, dst)

    def _prepare_metadata(self, nar_package_dir: Path) -> None:
        # Create the metadata directory
        metadata_dir = nar_package_dir / "META-INF"
        metadata_dir.mkdir()

        # Copy the legal files
        for legal_file in self._get_legal_files():
            if not legal_file.is_file():
                logger.debug(f"Skipping: {legal_file.as_posix()}")
                continue

            dest = metadata_dir / legal_file.relative_to(self._path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legal_file, dest)

        # Copy readme file/s if mentioned in pyproject.toml
        if "readme" in self._poetry.local_config:
            readme: str | Iterable[str] = self._poetry.local_config["readme"]

            if isinstance(readme, str):
                file = BuildIncludeFile(
                    path=readme,
                    project_root=self._path,
                    source_root=self._path,
                )
                shutil.copy2(file.path, metadata_dir / Path(readme).name)
            else:
                for r in readme:
                    file = BuildIncludeFile(
                        path=r,
                        project_root=self._path,
                        source_root=self._path,
                    )
                    shutil.copy2(file.path, metadata_dir / Path(r).name)

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

    def _copy_folder(self, nar: ZipFile, nar_package_dir: Path) -> None:
        for file in sorted(nar_package_dir.glob("**/*")):
            if not (file.is_file() or file.is_dir()):
                continue

            target_path = file.relative_to(nar_package_dir)
            self._add_file(nar, file, target_path)

    def _prepare_dependencies(
        self, target_dir: Path, nar_package_dir: Path
    ) -> None:
        # Create a temporary requirements.txt file
        fd, tmp_file_path = tempfile.mkstemp(suffix=".txt")

        try:
            # command to export the requirements to a requirements.txt file
            command = [
                "poetry",
                "export",
                "-f",
                "requirements.txt",
                "-o",
                tmp_file_path,
            ]

            self._execute_command(command)

            # directory to store the pip cache
            cache_dir = target_dir / "pip-cache"

            if not cache_dir.exists():
                cache_dir.mkdir()

            # directory to unpack the dependencies
            deps_dir = nar_package_dir / "NAR-INF" / "bundled-dependencies"
            deps_dir.mkdir(parents=True)

            # command to download the dependencies
            # to the dependency unpack directory
            command = [
                str(self.executable),
                "-m",
                "pip",
                "install",
                "-r",
                tmp_file_path,
                "--upgrade",
                "--no-python-version-warning",
                "--no-input",
                "--cache-dir",
                str(cache_dir),
                "--quiet",
                "--target",
                str(deps_dir),
            ]

            self._execute_command(command)
        finally:
            os.close(fd)
            os.remove(tmp_file_path)

    def _execute_command(self, command: list[str]) -> None:
        # run the command to export the requirements
        check_call(command, stdout=PIPE, stderr=PIPE, cwd=self._path)

    def _add_file(
        self, nar: ZipFile, full_path: Path, rel_path: Path
    ) -> None:
        # We always want to have /-separated paths
        # in the zip file and in RECORD
        rel_path_name = (
            rel_path.as_posix()
            if full_path.is_file()
            else rel_path.as_posix() + "/"
        )
        zip_info = ZipInfo(rel_path_name)

        # Normalize permission bits to either 755 (executable) or 644
        st_mode = full_path.stat().st_mode
        new_mode = normalize_file_permissions(st_mode)
        zip_info.external_attr = (new_mode & 0xFFFF) << 16  # Unix attributes

        if stat.S_ISDIR(st_mode):
            zip_info.external_attr |= 0x10  # MS-DOS directory flag

        if full_path.is_dir():
            nar.writestr(zip_info, "")
        else:
            with full_path.open("rb") as src:
                src.seek(0)
                nar.writestr(zip_info, src.read(), compress_type=ZIP_DEFLATED)

    def _dynamic_metadata(self, nar_package_dir: Path) -> None:
        config = tomlkit.parse(
            self._poetry.pyproject_path.read_bytes().decode()
        )

        version = config.get("tool", {}).get("nar", {}).get("version", None)
        description = (
            config.get("tool", {}).get("nar", {}).get("description", None)
        )

        if version is not None:
            self._apply_dynamic_update(
                Path(version),
                nar_package_dir,
                r"version(?:\s+|)=(?:\s+|)?[\"']__version__[\"']",
                f'version = "{self._package.version}"',
            )

        if description is not None:
            self._apply_dynamic_update(
                Path(description),
                nar_package_dir,
                r"description(?:\s+|)=(?:\s+|)?[\"']__description__[\"']",
                f'description = "{self._package.description}"',
            )

    def _apply_dynamic_update(
        self,
        file_path: Path,
        nar_package_dir: Path,
        pattern: str,
        replace: str,
    ) -> None:
        files = self.find_files_to_add()

        flag = False

        # sorting everything so the order is stable.
        for file in sorted(files, key=lambda x: x.path):
            if file.relative_to_project_root() == file_path:
                flag = True
                x = nar_package_dir / file.relative_to_target_root()

                with x.open("r+b") as src:
                    lines = re.sub(
                        pattern,
                        replace,
                        src.read().decode(),
                    )

                    src.seek(0)
                    src.write(lines.encode())
                    src.truncate()

                break

        if not flag:
            logger.warning(f"File {file_path} not found in the package")
