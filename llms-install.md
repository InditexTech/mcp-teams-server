## MCP Teams Server Installation Guide

This guide is specifically designed for AI agents like Cline to install and configure the MCP Teams Server for use 
with LLM applications like Claude Desktop, Cursor, Roo Code, and Cline.

### Overview

MCP Teams Server is a communication tool that allows AI assistants to interact with Microsoft Teams Channels.

### Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager
- [Python 3.12](https://www.python.org/)
- Microsoft Teams account with [proper set-up](./doc/MS-Teams-setup.md)

### Installation and configuration

Add the MCP server configuration to your MCP settings file based on your LLM client.

Remember there is a [pre-built image](https://github.com/InditexTech/mcp-teams-server/pkgs/container/mcp-teams-server) hosted in ghcr.io.
You can install this image by running the following command

```commandline
docker pull ghcr.io/inditextech/mcp-teams-server:latest
```

Sample docker setup:

```yaml
{
  "mcpServers": {
    "msteams": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "TEAMS_APP_ID",
        "-e",
        "TEAMS_APP_PASSWORD",
        "-e",
        "TEAMS_APP_TENANT_ID",
        "-e",
        "TEAM_ID",
        "-e",
        "TEAMS_CHANNEL_ID",
        "ghcr.io/inditextech/mcp-teams-server"
      ],
      "env": {
        "TEAMS_APP_ID": "<fill_me_with_proper_uuid>",
        "TEAMS_APP_PASSWORD": "<fill_me_with_proper_uuid>",
        "TEAMS_APP_TENANT_ID": "<fill_me_with_proper_uuid>",
        "TEAM_ID": "<fill_me_with_proper_uuid>",
        "TEAMS_CHANNEL_ID": "<fill_me_with_proper_channel_id>",
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      }
    }
  }
}
```

Sample Cline setup with docker through WSL (Windows only):

```yaml 
{
  "mcpServers": {
    "github.com/InditexTech/mcp-teams-server/tree/main": {
      "command": "wsl",
      "args": [
        "TEAMS_APP_ID=<fill_me_with_proper_uuid>",
        "TEAMS_APP_PASSWORD=<fill_me_with_proper_uuid>",
        "TEAMS_APP_TENANT_ID=<fill_me_with_proper_uuid>",
        "TEAM_ID=<fill_me_with_proper_uuid>",
        "TEAMS_CHANNEL_ID=<fill_me_with_proper_uuid>",
        "docker",
        "run",
        "-i",
        "--rm",
        "ghcr.io/inditextech/mcp-teams-server"
      ],
      "env": {
        "DOCKER_HOST": "unix:///var/run/docker.sock"
      },
      "disabled": false,
      "autoApprove": [ ],
      "timeout": 300
    }
  }
}
```

Sample local development setup:

```yaml
{
  "mcpServers": {
    "msteams": {
      "command": "uv",
      "args": [
        "run",
        "mcp-teams-server"
      ],
      "env": {
        "TEAMS_APP_ID": "<fill_me_with_proper_uuid>",
        "TEAMS_APP_PASSWORD": "<fill_me_with_proper_uuid>",
        "TEAMS_APP_TENANT_ID": "<fill_me_with_proper_uuid>",
        "TEAM_ID": "<fill_me_with_proper_uuid>",
        "TEAMS_CHANNEL_ID": "<fill_me_with_proper_channel_id>"
      }
    }
  }
}
```

### Verify installation

Once configured, you'll have access to these tools:

#### 1. start_thread

Start a new thread with a given title and content

**Parameters:**
- `title`: (Required) The thread title
- `content`: (Required) The thread content
- `member_name`: (Optional) Member name to mention in the thread

#### 2. update_thread

Update an existing thread with new content

**Parameters:**
- `thread_id`: (Required) The thread ID as a string in the format '1743086901347'
- `content`: (Required) The content to update in the thread
- `member_name`: (Optional) Member name to mention in the thread

#### 3. read_thread

Read replies in a thread

**Parameters:**
- `thread_id`: (Required) The thread ID as a string in the format '1743086901347'

#### 4. list_threads

List threads in channel with pagination

**Parameters:**
- `limit`: (Optional, default 50) Maximum number of items to retrieve or page size
- `cursor`: (Optional) Pagination cursor for the next page of results, returned by previous list_thread tool call.

#### 5. get_member_by_name

Get a member by its name

**Parameters:**
- `name`: (Required) Member name

#### 6. list_members

List all members in the team

## Usage Examples

Some ideas for user prompts are:

```
Please start a thread in teams with the following content... 
```

```
Please list members in team
```

```
Please perform this task... and send results to a new thread in teams. Remember to mention "User Name"
```

```
Please read latest team threads and reply to threads that mention "Your bot name" 
```


