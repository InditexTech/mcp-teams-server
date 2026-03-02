# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib import metadata

from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from msgraph.graph_service_client import GraphServiceClient
from pydantic import Field

from .config import BotConfiguration
from .teams import (
    PagedTeamsMessages,
    TeamsClient,
    TeamsMember,
    TeamsMessage,
    TeamsThread,
)

try:
    __version__ = metadata.version("mcp-teams-server")
except metadata.PackageNotFoundError:
    __version__ = "unknown"

# Load .env
load_dotenv()

# Config logging
logging.basicConfig(
    level=os.environ.get("MCP_LOGLEVEL", "ERROR"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)

LOGGER = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "TEAMS_APP_ID",
    "TEAMS_APP_PASSWORD",
    "TEAMS_APP_TYPE",
    "TEAMS_APP_TENANT_ID",
    "TEAM_ID",
    "TEAMS_CHANNEL_ID",
]


@dataclass
class AppContext:
    client: TeamsClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""

    # Bot adapter construction
    bot_config = BotConfiguration()
    connection_manager = MsalConnectionManager(**bot_config)
    adapter = CloudAdapter(connection_manager=connection_manager)

    # Graph client construction
    credentials = ClientSecretCredential(
        bot_config["APP_TENANT_ID"], bot_config["APP_ID"], bot_config["APP_PASSWORD"]
    )
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credentials, scopes=scopes)

    client = TeamsClient(
        adapter,
        graph_client,
        bot_config["APP_ID"],
        bot_config["TEAM_ID"],
        bot_config["TEAMS_CHANNEL_ID"],
    )
    yield AppContext(client=client)


mcp = FastMCP(
    "mcp-teams-server",
    lifespan=app_lifespan,
    dependencies=[
        "aiohttp",
        "asyncio",
        "botbuilder-core",
        "botbuilder-integration-aiohttp",
        "dotenv",
        "msgraph-sdk",
        "multidict",
    ],
)


def _get_teams_client(ctx: Context) -> TeamsClient:
    return ctx.request_context.lifespan_context.client


@mcp.tool(
    name="start_thread", description="Start a new thread with a given title and content"
)
async def start_thread(
    ctx: Context,
    title: str = Field(description="The thread title"),
    content: str = Field(description="The thread content"),
    member_name: str | None = Field(
        description="Member name to mention in the thread", default=None
    ),
) -> TeamsThread:
    await ctx.debug(f"start_thread with title={title} and content={content}")
    client = _get_teams_client(ctx)
    return await client.start_thread(title, content, member_name)


@mcp.tool(
    name="update_thread", description="Update an existing thread with new content"
)
async def update_thread(
    ctx: Context,
    thread_id: str = Field(
        description="The thread ID as a string in the format '1743086901347'"
    ),
    content: str = Field(description="The content to update in the thread"),
    member_name: str | None = Field(
        description="Member name to mention in the thread", default=None
    ),
) -> TeamsMessage:
    await ctx.debug(f"update_thread with thread_id={thread_id} and content={content}")
    client = _get_teams_client(ctx)
    return await client.update_thread(thread_id, content, member_name)


@mcp.tool(name="read_thread", description="Read replies in a thread")
async def read_thread(
    ctx: Context,
    thread_id: str = Field(
        description="The thread ID as a string in the format '1743086901347'"
    ),
) -> PagedTeamsMessages:
    await ctx.debug(f"read_thread with thread_id={thread_id}")
    client = _get_teams_client(ctx)
    return await client.read_thread_replies(thread_id, 50)


@mcp.tool(name="list_threads", description="List threads in channel with pagination")
async def list_threads(
    ctx: Context,
    limit: int = Field(
        description="Maximum number of items to retrieve or page size", default=50
    ),
    cursor: str | None = Field(
        description="Pagination cursor for the next page of results", default=None
    ),
) -> PagedTeamsMessages:
    await ctx.debug(f"list_threads with cursor={cursor} and limit={limit}")
    client = _get_teams_client(ctx)
    return await client.read_threads(limit, cursor)


@mcp.tool(name="get_member_by_name", description="Get a member by its name")
async def get_member_by_name(
    ctx: Context, name: str = Field(description="Member name")
):
    await ctx.debug(f"get_member_by_name with name={name}")
    client = _get_teams_client(ctx)
    return await client.get_member_by_name(name)


@mcp.tool(name="list_members", description="List all members in the team")
async def list_members(ctx: Context) -> list[TeamsMember]:
    await ctx.debug("list_members")
    client = _get_teams_client(ctx)
    return await client.list_members()


def _check_required_environment():
    exit_code = None
    for var in REQUIRED_ENV_VARS:
        value = os.environ.get(var)
        if value is None:
            LOGGER.info(f"Required ENV {var} not present")
            exit_code = 1
    if exit_code is not None:
        sys.exit(exit_code)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="MCP Teams Server to allow Microsoft Teams interaction"
    )

    default_transport = os.environ.get("MCP_TRANSPORT", "stdio")

    parser.add_argument(
        "-t",
        "--transport",
        nargs=1,
        type=str,
        help="MCP Server Transport: stdio or sse",
        default=default_transport,
        choices=["stdio", "sse"],
    )

    args = parser.parse_args()

    LOGGER.info(
        f'Starting MCP Teams Server "{__version__}" with transport "{args.transport}"'
    )
    _check_required_environment()
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
