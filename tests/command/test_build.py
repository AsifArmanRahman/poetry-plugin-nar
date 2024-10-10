# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil
import tarfile

from typing import TYPE_CHECKING

import pytest

from poetry.core.masonry.utils.helpers import distribution_name
from poetry.utils.env import EnvManager
from poetry.utils.env import VirtualEnv


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from cleo.testers.command_tester import CommandTester
    from poetry.poetry import Poetry

    from tests.types import CommandTesterFactory


def get_package_glob(poetry: Poetry) -> str:
    return (
        f"{distribution_name(poetry.package.name)}-{poetry.package.version}*"
    )


@pytest.fixture
def tmp_tester(
    poetry: Poetry, command_tester_factory: CommandTesterFactory
) -> CommandTester:
    return command_tester_factory("build", poetry)


@pytest.fixture
def tmp_venv(tmp_path: Path) -> Iterator[VirtualEnv]:
    venv_path = tmp_path / "venv"

    EnvManager.build_venv(venv_path, with_pip=True)

    venv = VirtualEnv(venv_path)
    yield venv

    shutil.rmtree(venv.path)


@pytest.mark.parametrize("project", ["simple-project"])
def test_build_format_is_not_valid(tmp_tester: CommandTester) -> None:
    with pytest.raises(ValueError, match=r"Invalid format.*"):
        tmp_tester.execute("--format not_valid")


@pytest.mark.parametrize(
    ("project", "format"),
    [
        (
            "simple-project",
            "sdist",
        ),
        (
            "simple-project",
            "wheel",
        ),
        (
            "simple-project",
            "all",
        ),
        (
            "pretty-print-json",
            "nar",
        ),
    ],
)
def test_build_creates_packages(
    tmp_tester: CommandTester,
    poetry: Poetry,
    project_dir: Path,
    format: str,
) -> None:
    tmp_tester.execute(f"--format {format}")
    build_artifacts = tuple(
        (project_dir / "dist").glob(get_package_glob(poetry))
    )
    assert len(build_artifacts) == 2 if format == "all" else 1
    assert all(archive.exists() for archive in build_artifacts)


@pytest.mark.parametrize("project", ["non-package-project"])
def test_build_not_possible_in_non_package_mode(
    tmp_tester: CommandTester,
) -> None:
    assert tmp_tester.execute() == 1
    assert (
        tmp_tester.io.fetch_error()
        == "Building a package is not possible in non-package mode.\n"
    )


@pytest.mark.parametrize("project", ["multiple-readme"])
def test_build_with_multiple_readme_files(
    poetry: Poetry,
    project_dir: Path,
    tmp_venv: VirtualEnv,
    command_tester_factory: CommandTesterFactory,
) -> None:
    tester = command_tester_factory("build", poetry, environment=tmp_venv)
    tester.execute("--format all")

    build_dir = project_dir / "dist"
    assert build_dir.exists()

    name = distribution_name(poetry.package.name)
    filename = f"{name}-{poetry.package.version}"

    sdist_file = build_dir / f"{filename}.tar.gz"
    assert sdist_file.exists()
    assert sdist_file.stat().st_size > 0

    (wheel_file,) = build_dir.glob(f"{filename}-*.whl")
    assert wheel_file.exists()
    assert wheel_file.stat().st_size > 0

    with tarfile.open(sdist_file) as tf:
        sdist_content = tf.getnames()

    assert f"{filename}/README-1.md" in sdist_content
    assert f"{filename}/README-2.md" in sdist_content


@pytest.mark.parametrize(
    ("project", "format", "output_dir"),
    [
        ("simple-project", "all", None),
        ("simple-project", "all", "dist"),
        ("simple-project", "all", "test/dir"),
        ("simple-project", "all", "../dist"),
        ("simple-project", "all", "absolute"),
    ],
)
def test_build_output_option(
    tmp_tester: CommandTester,
    project_dir: Path,
    poetry: Poetry,
    format: str,
    output_dir: str | None,
) -> None:
    if output_dir is None:
        tmp_tester.execute(f"-f {format}")
        build_dir = project_dir / "dist"
    elif output_dir == "absolute":
        tmp_tester.execute(f"-f {format} -o {project_dir / 'tmp/dist'}")
        build_dir = project_dir / "tmp/dist"
    else:
        tmp_tester.execute(f"-f {format} -o {output_dir}")
        build_dir = project_dir / output_dir

    build_artifacts = tuple(build_dir.glob(get_package_glob(poetry)))
    assert len(build_artifacts) == 2 if format == "all" else 1
    assert all(archive.exists() for archive in build_artifacts)
