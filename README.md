[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/inditextech-mcp-teams-server-badge.png)](https://mseep.ai/app/inditextech-mcp-teams-server)

[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=InditexTech_mcp-teams-server&metric=bugs)](https://sonarcloud.io/summary/new_code?id=InditexTech_mcp-teams-server)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=InditexTech_mcp-teams-server&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=InditexTech_mcp-teams-server)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=InditexTech_mcp-teams-server&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=InditexTech_mcp-teams-server)
![GitHub License](https://img.shields.io/github/license/InditexTech/mcp-teams-server)
![GitHub Release](https://img.shields.io/github/v/release/InditexTech/mcp-teams-server)
[![Scorecard](https://api.scorecard.dev/projects/github.com/InditexTech/mcp-teams-server/badge)](https://scorecard.dev/viewer/?uri=github.com/InditexTech/mcp-teams-server)
<!-- [![Best Practices](https://www.bestpractices.dev/projects/10400/badge)](https://www.bestpractices.dev/projects/10400) -->


# MCP Teams Server

An MCP ([Model Context Protocol](https://modelcontextprotocol.io/introduction)) server implementation for 
[Microsoft Teams](https://www.microsoft.com/en-us/microsoft-teams/group-chat-software/) integration, providing capabilities to 
read messages, create messages, reply to messages, mention members.

## Features

https://github.com/user-attachments/assets/548a9768-1119-4a2d-bd5c-6b41069fc522

- Start thread in channel with title and contents, mentioning users
- Update existing threads with message replies, mentioning users
- Read thread replies
- List channel team members
- Read channel messages

## Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager
- [Python 3.10](https://www.python.org/)
- Microsoft Teams account with [proper set-up](./doc/MS-Teams-setup.md)

## Installation

1. Clone the repository:

```bash
git clone [repository-url]
cd mcp-teams-server
```

2. Create a virtual environment and install dependencies:

```bash
uv venv
uv sync --frozen --all-extras --dev
```

## Teams configuration

Please read [this document](./doc/MS-Teams-setup.md) to help you to configure Microsoft Teams and required 
Azure resources. It is not a step-by-step guide but can help you figure out what you will need.

## Usage

Set up the following environment variables in your shell or in an .env file. You can use [sample file](./sample.env) 
as a template:

| Key                     | Description                                |
|-------------------------|--------------------------------------------|
| **TEAMS_APP_ID**        | UUID for your MS Entra ID application ID   |
| **TEAMS_APP_PASSWORD**  | Client secret                              |
| **TEAMS_APP_TYPE**      | SingleTenant or MultiTenant                |
| **TEAMS_APP_TENANT_ID** | Tenant uuid in case of SingleTenant        |
| **TEAM_ID**             | MS Teams Group Id or Team Id               |
| **TEAMS_CHANNEL_ID**    | MS Teams Channel ID with url escaped chars |

Start the server:

```bash
uv run mcp-teams-server
```

## Development

Integration tests require the set-up the following environment variables:

| Key                    | Description                    |
|------------------------|--------------------------------|
| **TEST_THREAD_ID**     | timestamp of the thread id     |
| **TEST_MESSAGE_ID**    | timestamp of the message id    |
| **TEST_USER_NAME**     | test user name                 |


```bash
uv run pytest -m integration
```

### Pre-built docker image

There is a [pre-built image](https://github.com/InditexTech/mcp-teams-server/pkgs/container/mcp-teams-server) hosted in ghcr.io.
You can install this image by running the following command

```commandline
docker pull ghcr.io/inditextech/mcp-teams-server:latest
```

### Build docker image

A docker image is available to run MCP server. You can build it with the following command:

```bash
docker build . -t inditextech/mcp-teams-server
```

### Run docker image

Basic run configuration:

```bash
docker run -it inditextech/mcp-teams-server
```

Run with environment variables from .env file:

```bash
docker run --env-file .env -it inditextech/mcp-teams-server
```

### Setup LLM to use MCP Teams Server

Please follow instructions on the [following document](./llms-install.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull
requests.

## Security

For security concerns, please see our [Security Policy](SECURITY.md).

## License

This project is licensed under the [Apache-2.0](LICENSE.txt) file for details.

© 2025 INDUSTRIA DE DISEÑO TEXTIL S.A. (INDITEX S.A.)
