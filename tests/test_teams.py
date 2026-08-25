# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import TurnContext
from msgraph.graph_service_client import GraphServiceClient

from mcp_teams_server.config import BotConfiguration
from mcp_teams_server.teams import DEFAULT_MEMBER_PAGE_SIZE, TeamsClient

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

LOGGER = logging.getLogger(__name__)


class FakeRepliesRequestBuilder:
    def __init__(self, response):
        self.response = response

    async def get(self, request_configuration=None):
        return self.response


class FakeChatMessageRequestBuilder:
    def __init__(self, replies_builder):
        self.replies = replies_builder


class FakeMessagesRequestBuilder:
    def __init__(self, replies_builder):
        self.replies_builder = replies_builder

    def by_chat_message_id(self, chat_message_id):
        return FakeChatMessageRequestBuilder(self.replies_builder)


class FakeChannelRequestBuilder:
    def __init__(self, replies_builder):
        self.messages = FakeMessagesRequestBuilder(replies_builder)


class FakeChannelsRequestBuilder:
    def __init__(self, replies_builder):
        self.replies_builder = replies_builder

    def by_channel_id(self, channel_id):
        return FakeChannelRequestBuilder(self.replies_builder)


class FakeTeamRequestBuilder:
    def __init__(self, replies_builder):
        self.channels = FakeChannelsRequestBuilder(replies_builder)


class FakeTeamsRequestBuilder:
    def __init__(self, replies_builder):
        self.replies_builder = replies_builder

    def by_team_id(self, team_id):
        return FakeTeamRequestBuilder(self.replies_builder)


class FakeAdapter:
    on_turn_error = None

    async def continue_conversation(
        self, agent_app_id=None, continuation_activity=None, callback=None
    ):
        if callback is not None:
            await callback(SimpleNamespace(activity=SimpleNamespace(service_url="url")))


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
        adapter,
        graph_client,
        config["APP_ID"],
        config["TEAM_ID"],
        config["TEAMS_CHANNEL_ID"],
    )


@pytest.mark.asyncio
async def test_read_thread_replies_returns_next_page_cursor():
    graph_response = SimpleNamespace(
        odata_next_link="next-cursor",
        odata_count=1,
        value=[
            SimpleNamespace(
                id="reply-id",
                reply_to_id="thread-id",
                body=SimpleNamespace(content="reply content"),
            )
        ],
    )
    replies_builder = FakeRepliesRequestBuilder(graph_response)
    graph_client = cast(
        GraphServiceClient,
        SimpleNamespace(teams=FakeTeamsRequestBuilder(replies_builder)),
    )
    adapter = cast(CloudAdapter, SimpleNamespace())
    client = TeamsClient(
        adapter,
        graph_client,
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )

    result = await client.read_thread_replies("thread-id", limit=25)

    assert result.cursor == "next-cursor"
    assert result.limit == 25
    assert result.total == 1
    assert result.items[0].message_id == "reply-id"


@pytest.mark.asyncio
async def test_list_members_reads_all_pages_with_configurable_page_size():
    calls = []
    pages = [
        SimpleNamespace(
            members=[
                SimpleNamespace(name="Ada Lovelace", email="ada@example.com"),
            ],
            continuation_token="next-page",
        ),
        SimpleNamespace(
            members=[
                SimpleNamespace(name="Grace Hopper", email="grace@example.com"),
            ],
            continuation_token=None,
        ),
    ]

    async def get_paged_team_members(context, teams_channel_id, page_size, token):
        calls.append((teams_channel_id, page_size, token))
        return pages.pop(0)

    client = TeamsClient(
        cast(CloudAdapter, FakeAdapter()),
        cast(GraphServiceClient, SimpleNamespace()),
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )

    with patch(
        "mcp_teams_server.teams.TeamsInfo.get_paged_team_members",
        side_effect=get_paged_team_members,
    ):
        result = await client.list_members(page_size=25)

    assert calls == [("channel-id", 25, ""), ("channel-id", 25, "next-page")]
    assert [member.name for member in result] == ["Ada Lovelace", "Grace Hopper"]


@pytest.mark.asyncio
async def test_get_mention_member_searches_all_pages():
    calls = []
    pages = [
        SimpleNamespace(
            members=[SimpleNamespace(name="Ada Lovelace", email="ada@example.com")],
            continuation_token="next-page",
        ),
        SimpleNamespace(
            members=[
                SimpleNamespace(
                    id="member-id", name="Grace Hopper", email="grace@example.com"
                ),
            ],
            continuation_token=None,
        ),
    ]

    async def get_paged_team_members(context, teams_channel_id, page_size, token):
        calls.append((teams_channel_id, page_size, token))
        return pages.pop(0)

    client = TeamsClient(
        cast(CloudAdapter, FakeAdapter()),
        cast(GraphServiceClient, SimpleNamespace()),
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )

    with patch(
        "mcp_teams_server.teams.TeamsInfo.get_paged_team_members",
        side_effect=get_paged_team_members,
    ):
        result = await client._get_mention_member(
            cast(TurnContext, SimpleNamespace()), "Grace Hopper"
        )

    assert calls == [
        ("channel-id", DEFAULT_MEMBER_PAGE_SIZE, ""),
        ("channel-id", DEFAULT_MEMBER_PAGE_SIZE, "next-page"),
    ]
    assert result is not None
    assert result.name == "Grace Hopper"


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
    try:
        result = await setup_teams_client.start_thread(
            "First thread", "First thread content with mention", user_name
        )
        print(f"Result {result}\n")
        assert result is not None
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_threads(setup_teams_client):
    try:
        result = await setup_teams_client.read_threads(50)
        print(f"Result {result}\n")
        assert result is not None
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_thread(setup_teams_client, thread_id, user_name):
    try:
        result = await setup_teams_client.update_thread(
            thread_id, "Thread updated content with mention", user_name
        )
        print(f"Result {result}\n")
        assert result is not None
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_thread_replies(setup_teams_client, thread_id):
    try:
        result = await setup_teams_client.read_thread_replies(thread_id)
        print(f"Result {result}\n")
        assert result is not None
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_members(setup_teams_client):
    try:
        result = await setup_teams_client.list_members()
        print(f"Result {result}\n")
        assert result is not None
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
