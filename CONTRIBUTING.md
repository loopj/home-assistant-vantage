# Contributing

First off, thanks for taking the time to contribute!

## Table of Contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [🔨 Set up Development Environment](#-set-up-development-environment)
- [✨ Submit your work](#-submit-your-work)
- [🎨 Style guidelines](#-style-guidelines)
- [🚀 Publish a release](#-publish-a-release)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## 🔨 Set up Development Environment

### Using `uv`

home-assistant-vantage uses [uv](https://docs.astral.sh/uv/) to run scripts, manage virtual environments, create reproducible builds, and publish packages. Check out the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) to get started.

To set up your development environment, run the following commands:

```bash
# Create a virtual environment
uv venv

# Install development dependencies
uv sync --extra dev
```

To start the Home Assistant development server, run:

```bash
uv run scripts/develop
```

### Manually

If you'd prefer to manage your own python environment, you can install the development dependencies manually.

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

To start the Home Assistant development server, run:

```bash
./scripts/develop
```

## ✨ Submit your work

Submit your improvements, fixes, and new features to one at a time, using GitHub [Pull Requests](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).

Good pull requests remain focused in scope and avoid containing unrelated commits. If your contribution involves a significant amount of work or substantial changes to any part of the project, please open an issue to discuss it first to avoid any wasted or duplicate effort.

## 🎨 Style guidelines

Before submitting a pull request, make sure your code follows the style guidelines. This project uses [pyright](https://microsoft.github.io/pyright/) for type checking, and [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

Pull requests will trigger a CI check that blocks merging if the code does not pass the style guidelines.

### Running checks automatically with vscode

If you are using vscode, you'll be prompted to install the recommended extensions when you open the workspace.

### Running checks manually

```bash
# Run type checking
uv run pyright
```

```bash
# Run linting
uv run ruff check
```

```bash
# Format code
uv run ruff format
```

## 🚀 Publish a release

First, update the version number:

```bash
bumpver update --patch # or --major --minor
```

Then [create a release on GitHub](https://github.com/loopj/home-assistant-vantage/releases/new). Releases are published automatically to HACS when a new GitHub release is created.
