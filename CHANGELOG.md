# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.14]

### Changed
- Upgraded project dependencies.

### Fixed
- Restricted Graph pagination cursors to the configured team, channel, and thread
  (reported by Syed Anas Mohiuddin).
- Corrected the documented scope of Microsoft Graph channel-message permissions.

## [1.0.13] - 2026-08-25

### Changed
- Migrated Teams integration from `microsoft-agents-hosting-teams` to
  `microsoft-agents-hosting-msteams`.
- Reworked member paging and lookup to use the Microsoft Teams connector client.
- Hardened the Docker image with a multi-stage build and a minimal non-root runtime.

## [1.0.12] - 2026-08-25

### Added
- Added configurable member paging and complete member lookup across all pages.
- Added MCP input validation for required strings, pagination limits, cursors, and
  member page size.
- Added pagination support to the `read_thread` tool.
- Added `streamable-http` transport support while retaining `sse` as a legacy
  option.
- Added unit coverage for pagination, validation schemas, error propagation, and
  lifespan cleanup.

### Changed
- Migrated from MCP Python SDK `1.28.1` to `2.1.0`.
- Replaced `FastMCP` with `MCPServer` and updated tests for v2 snake_case protocol
  fields.
- Hardened Teams message mapping for missing Graph response fields.
- Improved exception logging and callback error propagation.

### Removed
- Removed unused `read_message` implementation.

## [1.0.11] - 2026-08-24

### Changed
- Upgraded Python, MCP, Microsoft Graph SDK, pytest, pyright, ruff, setuptools, and related dependencies.
- Applied minor cosmetic fixes and dependency maintenance updates.

## [1.0.10] - 2026-06-12

### Changed
- Upgraded Dependabot-managed dependencies.

## [1.0.9] - 2026-05-13

### Changed
- Upgraded project dependencies and bumped the package version.

## [1.0.8] - 2026-03-16

### Changed
- Added security hardening changes after the Microsoft Agents SDK migration.

## [1.0.7] - 2026-03-04

### Changed
- Migrated Teams write operations to the Microsoft Agents SDK.
- Updated authentication and team channel member listing integration.
- Removed unused SonarCloud configuration and refreshed security/contribution documentation.

## [1.0.6] - 2025-07-21

### Changed
- Upgraded MCP, Microsoft Graph SDK, multidict, and related environment dependencies.

### Fixed
- Added a missing dependency required by the upgraded stack.

## [1.0.5] - 2025-06-03

### Changed
- Upgraded BotBuilder, aiohttp, MCP, Microsoft Graph SDK, and multidict dependencies.

## [1.0.4] - 2025-05-16

### Changed
- Upgraded Microsoft Graph SDK.

## [1.0.3] - 2025-04-24

### Fixed
- Updated dependency versions and corrected Dependabot configuration.

## [1.0.2] - 2025-04-24

### Added
- Added Dependabot configuration and OpenSSF Scorecard workflow.
- Added technical documentation and additional setup guidance.
- Added Docker image references and improved release/coverage workflow configuration.

### Fixed
- Fixed documentation typos, badges, CLA links, Docker image instructions, and Sonar workflow issues.

## [1.0.1] - 2025-04-02

### Added
- Added SonarCloud workflow setup and enhanced project documentation.

### Changed
- Reduced Docker startup overhead.
- Fixed REUSE compliance metadata.

## [1.0.0] - 2025-04-01

### Added
- First release of MCP Teams Server
- Basic Teams integration through MCP tools
- Documentation for setup and usage
- Security guidelines and policies
- Basic workflows for PR verify and release docker image
