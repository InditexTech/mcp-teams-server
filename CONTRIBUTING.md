# Contributing

Thank you for your interest in contributing to this project! We value and appreciate any contributions you can make.
To maintain a collaborative and respectful environment, please consider the following guidelines when contributing to
this project.

## Prerequisites

- Before starting to contribute to the code, you must first sign the Contributor License Agreement (CLA). Detailed
  instructions on how to proceed can be found in the
  [FOSS contributing guidelines](https://github.com/InditexTech/foss/blob/main/CONTRIBUTING.md).

## How to Contribute

1. Open an issue to discuss and gather feedback on the feature or fix you wish to address.
2. Fork the repository and clone it to your local machine.
3. Create a new branch to work on your contribution: `git checkout -b your-branch-name`.
4. Make the necessary changes in your local branch.
5. Ensure that your code follows the established project style and formatting guidelines.
6. Perform testing to ensure your changes do not introduce errors.
7. Make clear and descriptive commits that explain your changes.
8. Push your branch to the remote repository: `git push origin your-branch-name`.
9. Open a pull request describing your changes and linking the corresponding issue.
10. Await comments and discussions on your pull request. Make any necessary modifications based on the received feedback.
11. Once your pull request is approved, your contribution will be merged into the main branch.

## Contribution Guidelines

- All contributors are expected to follow the project's [code of conduct](CODE_of_CONDUCT.md). Please be respectful and
considerate towards other contributors.
- Before starting work on a new feature or fix, check existing [issues](../../issues) and [pull requests](../../pulls)
to avoid duplications and unnecessary discussions.
- If you wish to work on an existing issue, comment on the issue to inform other contributors that you are working on it.
This will help coordinate efforts and prevent conflicts.
- It is always advisable to discuss and gather feedback from the community before making significant changes to the
project's structure or architecture.
- Ensure a clean and organized commit history. Divide your changes into logical and descriptive commits. We recommend to use the [Conventional Commits Specification](https://www.conventionalcommits.org/en/v1.0.0/)
- Document any new changes or features you add. This will help other contributors and project users understand your work
and its purpose.
- Be sure to link the corresponding issue in your pull request to maintain proper tracking of contributions.
- Remember to add license and copyright information following the [REUSE Specification](https://reuse.software/spec/#copyright-and-licensing-information).

## Development

Make sure that you have:

- Read the rest of the [`CONTRIBUTING.md`](CONTRIBUTING.md) sections.
- Meet the [prerequisites](#prerequisites).
- [uv](https://github.com/astral-sh/uv) installed
- [python](https://www.python.org/) 3.10 or later installed
- Set up integration with Microsoft Teams by your own means
- Run integration tests to verify Microsoft Teams integration

Please remember tu run linting locally before committing any changes:

```bash
uv run ruff check . --fix
uv run ruff format .
```

It is recommended to run a type checker:

```bash
uv run pyright
```

## Technical details

This MCP is built using [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) for Python from Anthropic.
It uses FastMCP to implement tools offered by the MCP server.

This MCP server consumes two Microsoft APIs / frameworks:

- [Azure Bot Builder](https://github.com/microsoft/botbuilder-python) for python
- [Microsoft Graph SDK](https://github.com/microsoftgraph/msgraph-sdk-python) for python

Azure Bot Builder allows a bot (Microsoft Entra ID app) to consume a Microsoft REST API to send messages to channels 
(but it is not capable of consuming messages because the bot is not deployed in Azure). The REST API client is 
encapsulated inside the framework classes, and it is not used directly.
In order to send messages without actually being deployed in Azure, the bot "continues" a conversation to retrieve 
the TurnContext instance and perform actions on "activities". This technique is called 
[proactive messaging](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages?tabs=python)

Replying to messages through bot builder is not possible without the help of 
[this hack](https://github.com/microsoft/botframework-sdk/issues/6626), because the bot builder framework 
is not ready for this use (although the internal REST API allows it, and it works like a charm).

Azure Bot Builder allows to perform any write operation, but reading messages or previous threads is not possible 
without a special "migration" permission. Because of that, we have preferred to use Microsoft Graph to read messages.
Microsoft Application Entra ID must have been granted permissions to read messages in a channel.

