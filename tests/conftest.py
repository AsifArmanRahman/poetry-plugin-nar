# SPDX-FileCopyrightText: © 2024 Asif Arman Rahman <asifarmanrahman@gmail.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import shutil

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.config.dict_config_source import DictConfigSource
from poetry.factory import Factory

from tests.helpers import Config
from tests.helpers import PoetryTestApplication


if TYPE_CHECKING:
    from poetry.poetry import Poetry
    from pytest_mock.plugin import MockerFixture

    from tests.types import FixtureDirGetter
    from tests.types import ProjectFactory


@pytest.fixture
def project_dir(tmp_path: Path, project: str) -> Path:
    return tmp_path / project


@pytest.fixture
def auth_config_source() -> DictConfigSource:
    source = DictConfigSource()

    return source


@pytest.fixture
def config_cache_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".cache" / "pypoetry"
    path.mkdir(parents=True)

    return path


@pytest.fixture
def config_source(config_cache_dir: Path) -> DictConfigSource:
    source = DictConfigSource()
    source.add_property("cache-dir", str(config_cache_dir))

    return source


@pytest.fixture
def config(
    config_source: DictConfigSource,
    auth_config_source: DictConfigSource,
    mocker: MockerFixture,
) -> Config:
    import keyring

    from keyring.backends.fail import Keyring

    keyring.set_keyring(Keyring())  # type: ignore[no-untyped-call]

    c = Config()
    c.merge(config_source.config)
    c.set_config_source(config_source)
    c.set_auth_config_source(auth_config_source)

    mocker.patch("poetry.config.config.Config.create", return_value=c)
    mocker.patch("poetry.config.config.Config.set_config_source")

    return c


@pytest.fixture
def project_factory(
    config: Config,
    project_dir: Path,
) -> ProjectFactory:
    def _factory(
        source: Path,
    ) -> Poetry:
        project_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, project_dir)

        poetry = Factory().create_poetry(project_dir)
        poetry.set_config(config)

        return poetry

    return _factory


@pytest.fixture(scope="session")
def fixture_base() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_dir(fixture_base: Path) -> FixtureDirGetter:
    def _fixture_dir(name: str) -> Path:
        return fixture_base / name

    return _fixture_dir


@pytest.fixture
def poetry(
    project: str,
    project_factory: ProjectFactory,
    fixture_dir: FixtureDirGetter,
) -> Poetry:
    return project_factory(source=fixture_dir(project))


@pytest.fixture
def app(poetry: Poetry) -> PoetryTestApplication:
    app_ = PoetryTestApplication(poetry)

    return app_
