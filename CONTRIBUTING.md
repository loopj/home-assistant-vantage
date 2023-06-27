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

To set up your development environment, you can either use a venv or a devcontainer.

### Using a Virtual Environment (recommended)

Create a venv in the root of the project:

```bash
python3 -m venv venv
```

Activate the venv:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
./scripts/setup
```

Start Home Assistant:

```bash
./scripts/develop
```

### Using a Development Container

> **Note**
> Using a development container is not as fast as a venv, and zeroconf discovery will not work.

Alternatively, you can use a [Development Container](https://containers.dev/) to set up your development environment. You'll need [Docker](https://www.docker.com/) and [Visual Studio Code](https://code.visualstudio.com/) installed, as well as the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension for Visual Studio Code.

Open the project in Visual Studio Code, and you should be prompted to reopen the project in a container. If you are not prompted, you can open the command palette and select *Dev Containers: Reopen in Container*.

Once the container is running, you can start Home Assistant by either running `./scripts/start` in the terminal, or by opening the command palette and selecting *Tasks: Run Task* and then *Run Home Assistant*.

## ✨ Submit your work

Submit your improvements, fixes, and new features to one at a time, using GitHub [Pull Requests](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).

Good pull requests remain focused in scope and avoid containing unrelated commits. If your contribution involves a significant amount of work or substantial changes to any part of the project, please open an issue to discuss it first to avoid any wasted or duplicate effort.

## 🎨 Style guidelines

This project uses [pre-commit](https://pre-commit.com/) to run code linting and formatting checks before commits are made. `pre-commit` and its associated hooks will automatically be installed when you run `./scripts/setup`.

To install `pre-commit` hook manually, run the following:

```bash
pre-commit install
```

You can invoke the pre-commit hook by hand at any time with:

```bash
pre-commit run
```

If you have already committed files before setting up the pre-commit hook with `pre-commit install`, you can fix everything up using `pre-commit run --all-files`. You need to make the fixing commit yourself after that.

## 🚀 Publish a release

Update the version number in `custom_components/vantage/manifest.json`, and commit the change to source control.

```bash
git add custom_components/vantage/manifest.json
git commit -m "Preparing release v1.2.3"
```

Tag the release, eg:

```bash
git tag v1.2.3
git push && git push --tags
```

Releases are published automatically to HACS when a new tag is pushed to the repository.
