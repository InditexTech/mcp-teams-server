# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys

import pytest
from azure.identity.aio import ClientSecretCredential
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from dotenv import load_dotenv
from msgraph.graph_service_client import GraphServiceClient

from mcp_teams_server.config import BotConfiguration
from mcp_teams_server.teams import TeamsClient

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.fixture()
def setup_teams_client() -> TeamsClient:
    # Cloud adapter
    config = BotConfiguration()
    connection_manager = MsalConnectionManager(**config)
    adapter = CloudAdapter(connection_manager=connection_manager)

    # Graph client
    credentials = ClientSecretCredential(
        config["APP_TENANT_ID"], config["APP_ID"], config["APP_PASSWORD"]
    )
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credentials, scopes=scopes)

    return TeamsClient(
        adapter, graph_client, config["APP_ID"], config["TEAM_ID"], config["TEAMS_CHANNEL_ID"]
    )


@pytest.fixture()
def thread_id() -> str | None:
    return os.environ.get("TEST_THREAD_ID")


@pytest.fixture()
def message_id() -> str | None:
    return os.environ.get("TEST_MESSAGE_ID")


@pytest.fixture()
def user_name() -> str | None:
    return os.environ.get("TEST_USER_NAME")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_thread(setup_teams_client, user_name):
    LOGGER.info(
        f"test_start_thread in team: {setup_teams_client.team_id} "
        f"and channel {setup_teams_client.teams_channel_id}"
    )
    result = await setup_teams_client.start_thread(
        "First thread", "First thread content with mention", user_name
    )
    print(f"Result {result}\n")
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_threads(setup_teams_client):
    result = await setup_teams_client.read_threads(50)
    print(f"Result {result}\n")
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_thread(setup_teams_client, thread_id, user_name):
    result = await setup_teams_client.update_thread(
        thread_id, "Thread updated content with mention", user_name
    )
    print(f"Result {result}\n")
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_thread_replies(setup_teams_client, thread_id):
    result = await setup_teams_client.read_thread_replies(thread_id)
    print(f"Result {result}\n")
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_members(setup_teams_client):
    result = await setup_teams_client.list_members()
    print(f"Result {result}\n")
    assert result is not None
