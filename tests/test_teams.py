# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging
import os
import sys
from types import SimpleNamespace
from typing import cast

import pytest
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv
from microsoft_agents.activity import ConversationAccount
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
    def __init__(self, replies_builder, response=None):
        self.replies_builder = replies_builder
        self.response = response
        self.url = None

    def by_chat_message_id(self, chat_message_id):
        return FakeChatMessageRequestBuilder(self.replies_builder)

    def with_url(self, url):
        self.url = url
        return self

    async def get(self, request_configuration=None):
        return self.response


class FakeTeamsConnectorClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def get_conversation_paged_member(
        self, conversation_id, page_size, continuation_token
    ):
        self.calls.append((conversation_id, page_size, continuation_token))
        if isinstance(self.responses, list):
            return self.responses.pop(0)
        return self.responses

    async def get_conversation_member(self, conversation_id, member_id):
        self.calls.append((conversation_id, member_id))
        return self.responses


class FakeChannelRequestBuilder:
    def __init__(self, replies_builder, response=None):
        self.messages = FakeMessagesRequestBuilder(replies_builder, response)


class FakeChannelsRequestBuilder:
    def __init__(self, replies_builder, response=None):
        self.replies_builder = replies_builder
        self.response = response

    def by_channel_id(self, channel_id):
        return FakeChannelRequestBuilder(self.replies_builder, self.response)


class FakeTeamRequestBuilder:
    def __init__(self, replies_builder, response=None):
        self.channels = FakeChannelsRequestBuilder(replies_builder, response)


class FakeTeamsRequestBuilder:
    def __init__(self, replies_builder, response=None):
        self.replies_builder = replies_builder
        self.response = response
        self.team = FakeTeamRequestBuilder(self.replies_builder, self.response)

    def by_team_id(self, team_id):
        return self.team


class FakeAdapter:
    on_turn_error = None

    def __init__(self, connector_client=None):
        self.connector_client = connector_client

    async def continue_conversation(
        self, agent_app_id=None, continuation_activity=None, callback=None
    ):
        if callback is not None:
            await callback(
                SimpleNamespace(
                    activity=SimpleNamespace(service_url="url"),
                    turn_state={"ConnectorClient": self.connector_client},
                )
            )


class FakeStartThreadAdapter:
    on_turn_error = None

    def __init__(self, responses=None, exception=None):
        self.responses = responses
        self.exception = exception

    async def continue_conversation(
        self, agent_app_id=None, continuation_activity=None, callback=None
    ):
        if callback is not None:
            await callback(
                SimpleNamespace(
                    activity=SimpleNamespace(
                        service_url="url",
                        conversation=ConversationAccount(id="conversation-id"),
                    )
                )
            )

    async def send_activities(self, context, activities):
        if self.exception is not None:
            raise self.exception
        return self.responses


class FakeUpdateThreadAdapter:
    on_turn_error = None

    def __init__(self, response=None):
        self.response = response

    async def continue_conversation(
        self, agent_app_id=None, continuation_activity=None, callback=None
    ):
        if callback is not None:
            await callback(
                SimpleNamespace(
                    activity=SimpleNamespace(
                        service_url="url",
                        conversation=ConversationAccount(id="conversation-id"),
                    ),
                    turn_state={
                        "ConnectorClient": SimpleNamespace(
                            conversations=SimpleNamespace(
                                send_to_conversation=self.send_to_conversation
                            )
                        )
                    },
                )
            )

    async def send_to_conversation(self, conversation_id, body):
        return self.response


def create_test_client(adapter, graph_client=None) -> TeamsClient:
    return TeamsClient(
        cast(CloudAdapter, adapter),
        cast(GraphServiceClient, graph_client or SimpleNamespace()),
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )


@pytest.fixture
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
async def test_read_threads_defaults_total_and_missing_body_content():
    graph_response = SimpleNamespace(
        odata_next_link=None,
        value=[SimpleNamespace(id="message-id")],
    )
    graph_client = cast(
        GraphServiceClient,
        SimpleNamespace(teams=FakeTeamsRequestBuilder(None, graph_response)),
    )
    client = TeamsClient(
        cast(CloudAdapter, SimpleNamespace()),
        graph_client,
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )

    result = await client.read_threads(limit=10)

    assert result.total == 1
    assert result.items[0].message_id == "message-id"
    assert result.items[0].thread_id == "message-id"
    assert result.items[0].content is None


@pytest.mark.asyncio
async def test_read_thread_replies_defaults_total_and_missing_fields():
    graph_response = SimpleNamespace(
        odata_next_link=None,
        value=[SimpleNamespace(id="reply-id")],
    )
    replies_builder = FakeRepliesRequestBuilder(graph_response)
    graph_client = cast(
        GraphServiceClient,
        SimpleNamespace(teams=FakeTeamsRequestBuilder(replies_builder)),
    )
    client = TeamsClient(
        cast(CloudAdapter, SimpleNamespace()),
        graph_client,
        teams_app_id="app-id",
        team_id="team-id",
        teams_channel_id="channel-id",
    )

    result = await client.read_thread_replies("thread-id", limit=10)

    assert result.total == 1
    assert result.items[0].message_id == "reply-id"
    assert result.items[0].thread_id == "thread-id"
    assert result.items[0].content is None


@pytest.mark.asyncio
async def test_start_thread_raises_when_send_fails():
    client = create_test_client(
        FakeStartThreadAdapter(exception=RuntimeError("send failed"))
    )

    with pytest.raises(RuntimeError, match="send failed"):
        await client.start_thread("title", "content")


@pytest.mark.asyncio
async def test_start_thread_raises_when_response_is_missing():
    client = create_test_client(FakeStartThreadAdapter(responses=[]))

    with pytest.raises(RuntimeError, match="thread creation response"):
        await client.start_thread("title", "content")


@pytest.mark.asyncio
async def test_update_thread_raises_when_response_is_missing():
    client = create_test_client(FakeUpdateThreadAdapter(response=None))

    with pytest.raises(RuntimeError, match="thread update response"):
        await client.update_thread("thread-id", "content")


@pytest.mark.asyncio
async def test_list_members_reads_all_pages_with_configurable_page_size():
    pages = [
        SimpleNamespace(
            members=[
                SimpleNamespace(
                    id="member-1",
                    name="Ada Lovelace",
                    email="ada@example.com",
                ),
            ],
            continuation_token="next-page",
        ),
        SimpleNamespace(
            members=[
                SimpleNamespace(
                    id="member-2",
                    name="Grace Hopper",
                    email="grace@example.com",
                ),
            ],
            continuation_token=None,
        ),
    ]
    connector_client = FakeTeamsConnectorClient(pages)
    client = create_test_client(FakeAdapter(connector_client))

    result = await client.list_members(page_size=25)

    assert connector_client.calls == [
        ("channel-id", 25, ""),
        ("channel-id", 25, "next-page"),
    ]
    assert [member.name for member in result] == ["Ada Lovelace", "Grace Hopper"]
    assert [member.id for member in result] == ["member-1", "member-2"]


@pytest.mark.asyncio
async def test_get_mention_member_searches_all_pages():
    pages = [
        SimpleNamespace(
            members=[
                SimpleNamespace(
                    id="member-1",
                    name="Ada Lovelace",
                    email="ada@example.com",
                )
            ],
            continuation_token="next-page",
        ),
        SimpleNamespace(
            members=[
                SimpleNamespace(
                    id="member-id",
                    name="Grace Hopper",
                    email="grace@example.com",
                ),
            ],
            continuation_token=None,
        ),
    ]
    connector_client = FakeTeamsConnectorClient(pages)
    client = create_test_client(FakeAdapter(connector_client))

    result = await client._get_mention_member(
        cast(
            TurnContext,
            SimpleNamespace(turn_state={"ConnectorClient": connector_client}),
        ),
        "Grace Hopper",
    )

    assert connector_client.calls == [
        ("channel-id", DEFAULT_MEMBER_PAGE_SIZE, ""),
        ("channel-id", DEFAULT_MEMBER_PAGE_SIZE, "next-page"),
    ]
    assert result is not None
    assert result.id == "member-id"
    assert result.name == "Grace Hopper"


@pytest.fixture
def thread_id() -> str | None:
    return os.environ.get("TEST_THREAD_ID")


@pytest.fixture
def message_id() -> str | None:
    return os.environ.get("TEST_MESSAGE_ID")


@pytest.fixture
def user_name() -> str | None:
    return os.environ.get("TEST_USER_NAME")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_thread(setup_teams_client, user_name):
    LOGGER.info(
        f"test_start_thread in team: {setup_teams_client.team_id} "
        f"and channel {setup_teams_client.teams_channel_id}"
    )
    result = None
    try:
        result = await setup_teams_client.start_thread(
            "First thread", "First thread content with mention", user_name
        )
        print(f"Result {result}\n")
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_threads(setup_teams_client):
    result = None
    try:
        result = await setup_teams_client.read_threads(50)
        print(f"Result {result}\n")
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_thread(setup_teams_client, thread_id, user_name):
    result = None
    try:
        result = await setup_teams_client.update_thread(
            thread_id, "Thread updated content with mention", user_name
        )
        print(f"Result {result}\n")
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_thread_replies(setup_teams_client, thread_id):
    result = None
    try:
        result = await setup_teams_client.read_thread_replies(thread_id)
        print(f"Result {result}\n")
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_members(setup_teams_client):
    result = None
    try:
        result = await setup_teams_client.list_members()
        print(f"Result {result}\n")
    except Exception as ex:
        LOGGER.error(ex)
        pytest.fail(str(ex))
    assert result is not None
