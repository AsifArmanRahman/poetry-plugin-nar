# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import re

from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from poetry.core.masonry.utils.helpers import distribution_name

from poetry_plugin_nar.nar import NarBuilder


if TYPE_CHECKING:
    from pathlib import Path

    from poetry.poetry import Poetry

    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.mark.parametrize("project", ["pretty-print-json"])
def test_build_package_manifest(poetry: Poetry, project_dir: Path) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        assert "META-INF/MANIFEST.MF" in file.namelist()

        manifest = file.read("META-INF/MANIFEST.MF").decode()

        assert "Manifest-Version: 1.0" in manifest
        assert "Created-By: poetry-plugin-nar" in manifest
        assert f"Nar-Id: {poetry.package.name}-nar" in manifest
        assert f"Nar-Group: {poetry.package.name}" in manifest
        assert f"Nar-Version: {poetry.package.version}" in manifest


@pytest.mark.parametrize(
    ("project", "target_dir"),
    [
        ("pretty-print-json", None),
        ("pretty-print-json", "dist"),
        ("pretty-print-json", "dist/build"),
    ],
)
def test_build_package_target_dir(
    poetry: Poetry,
    project_dir: Path,
    target_dir: str | None,
) -> None:
    NarBuilder(poetry).build(
        target_dir=project_dir / target_dir if target_dir else None
    )

    name = distribution_name(poetry.package.name)
    nar = (
        project_dir / target_dir if target_dir else project_dir / "dist"
    ) / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()


@pytest.mark.parametrize("project", ["package-in-src"])
def test_build_package_from_packages(
    poetry: Poetry, project_dir: Path
) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        assert f"{name}/__init__.py" in file.namelist()


@pytest.mark.parametrize("project", ["multiple-readme"])
def test_build_multiple_readme(poetry: Poetry, project_dir: Path) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        assert "META-INF/README-1.md" in file.namelist()
        assert "META-INF/README-2.md" in file.namelist()


@pytest.mark.parametrize("project", ["package-with-license"])
def test_build_with_license(poetry: Poetry, project_dir: Path) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        assert "META-INF/LICENSE" in file.namelist()


@pytest.mark.parametrize("project", ["write-numpy-version"])
def test_build_package_with_dependency(
    poetry: Poetry, project_dir: Path
) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        assert "META-INF/MANIFEST.MF" in file.namelist()

        manifest = file.read("META-INF/MANIFEST.MF").decode()

        assert "Manifest-Version: 1.0" in manifest
        assert "Created-By: poetry-plugin-nar" in manifest
        assert f"Nar-Id: {poetry.package.name}-nar" in manifest
        assert f"Nar-Group: {poetry.package.name}" in manifest
        assert f"Nar-Version: {poetry.package.version}" in manifest

        assert "META-INF/README.md" in file.namelist()
        assert "META-INF/LICENSE" in file.namelist()

        assert f"{name}/__init__.py" in file.namelist()

        assert (
            "NAR-INF/bundled-dependencies/numpy/__init__.py"
            in file.namelist()
        )
        assert any(
            re.search(
                r"NAR-INF/bundled-dependencies/numpy-\d+\.\d+\.\d+\.dist-info/WHEEL",
                f,
            )
            for f in file.namelist()
        )


@pytest.mark.parametrize("project", ["package-format-nar"])
def test_build_package_with_restricted_to_nar(
    project: str,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
) -> None:
    with pytest.raises(
        RuntimeError, match="format must be valid exactly by one definition"
    ):
        project_factory(source=fixture_dir(project))


@pytest.mark.parametrize("project", ["dynamic-package"])
def test_build_package_dynamic_metadata(
    poetry: Poetry, project_dir: Path
) -> None:
    NarBuilder(poetry).build()

    name = distribution_name(poetry.package.name)
    nar = project_dir / "dist" / f"{name}-{poetry.package.version}.nar"

    assert nar.exists()

    with ZipFile(nar, "r") as file:
        file.testzip()

        metadata = file.read(f"{name}/processor.py").decode()

        assert f'version = "{poetry.package.version}"' in metadata
        assert f'description = "{poetry.package.description}"' in metadata
