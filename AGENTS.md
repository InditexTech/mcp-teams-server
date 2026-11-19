## Overview

This project is a MCP server built with FastMCP and Python 3.12 to interact with a given channel in a Microsoft Team.
Microsoft 365 Agents SDK is used to write messages to Microsoft Teams and Microsoft Graph SDK is used for reads.

## Project structure

- `src/` source code
- `tests/` tests
- `doc/` user documentation

## Dev environment tips

 - Remember to unset `UV_DEFAULT_INDEX`, `UV_INDEX_INDITEX_ARTIFACTS_PUBLIC_USERNAME`, `UV_INDEX_INDITEX_ARTIFACTS_PUBLIC_PASSWORD` before using `uv` to run or build the project. It will make `uv` use pypi hosted dependencies.
 - Check if `.env` exists, it contains environment required to run integration tests. This file must be ignored in git and its contents must not be leaked.
 - Use `gh` and `git` tools to work with the repository.

## Testing instructions

- Always run integration tests: `uv run pytest -m integration`
- Always build docker image locally `docker build . -t inditextech/mcp-teams-server`

## PR instructions

- Always run `uv run ty check`, `uv run ruff check . --fix` and `uv run ruff format .` before committing.
- Use conventional commits.
- Update CHANGELOG.md from github PRs and releases history.

## Release instructions

- Increment the `[project].version` value in `pyproject.toml` for every release; the release tag is inferred from this version.
- Add the new version and a concise summary of user-visible, fixed, and security changes to `CHANGELOG.md`.
- Create a GitHub issue describing the release scope with `gh issue create` before creating release work.
- Create a branch linked to that issue with `gh sherpa create-branch --issue <number>`.
- Commit only the intended release files with a conventional commit message and `git commit -s` to add the required `Signed-off-by` trailer; do not include `.env` or unrelated local files.
- Create the release PR with `gh sherpa create-pr --issue <number> --label kind/release`.
- The `kind/release` label triggers the release process when the PR is closed/merged.
- Run dependency auditing, lock checks, static checks, unit tests, integration tests, and the required local Docker build before completing a security or dependency release.
- If a release fails after tag creation, remove the existing version tag before retrying, as documented in `RELEASE.md`.
