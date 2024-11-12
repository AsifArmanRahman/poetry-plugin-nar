<div align="center">
    <h1>Poetry Plugin Nar</h1>
    <p>Poetry plugin for building Apache NiFi NAR bundles.</p>
    <br>
</div>

<div align="center">
    <a href="https://python-poetry.org/">
        <img alt="Poetry" style="padding: 1px" src="https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json">
    </a>
    <a href="https://github.com/astral-sh/ruff">
        <img alt="Ruff" style="padding: 1px;" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json">
    </a>
    <a href="https://github.com/python/mypy">
        <img alt="mypy" style="padding: 1px" src="https://img.shields.io/badge/types-Mypy-blue.svg">
    </a>
</div>

<div align="center">
   <a href="https://github.com/AsifArmanRahman/poetry-plugin-nar/actions/workflows/tests.yml">
      <img alt="GitHub Workflow Tests Status" style="padding: 1px" src="https://img.shields.io/github/actions/workflow/status/asifarmanrahman/poetry-plugin-nar/tests.yml?label=tests&logo=Pytest">
   </a>
    <a href="https://github.com/AsifArmanRahman/poetry-plugin-nar/blob/main/LICENSE">
        <img alt="MIT" style="padding: 1px" src="https://img.shields.io/github/license/asifarmanrahman/poetry-plugin-nar">
    </a>
</div>


## Installation

The easiest way to install this plugin is via the `self add` command of Poetry.

```bash
poetry self add poetry-plugin-nar@git+https://github.com/AsifArmanRahman/poetry-plugin-nar@main
```

If you used `pipx` to install Poetry you can add the plugin via the `pipx inject` command.

```bash
pipx inject poetry poetry-plugin-nar@git+https://github.com/AsifArmanRahman/poetry-plugin-nar@main
```

Otherwise, if you used `pip` to install Poetry you can add the plugin packages via the `pip install` command.

```bash
pip install poetry-plugin-nar@git+https://github.com/AsifArmanRahman/poetry-plugin-nar@main
```

## Usage

The plugin extends the existing [build](https://python-poetry.org/docs/cli/#build) command of Poetry to add 'nar' as an option for format flag to build NAR packages.

```bash
poetry build -f nar
```

<br>

> **Note:**
> Due to the nature of Poetry schema as of now, it is not possible to restrict `packages` or `include` files only to nar format. Therefore, packages and include files will be included in the nar package only if no format is specified.
