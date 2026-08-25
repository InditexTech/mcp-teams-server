# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging

from kiota_abstractions.base_request_configuration import RequestConfiguration
from microsoft_agents.activity import (
    Activity,
    ChannelAccount,
    ConversationAccount,
    Mention,
)
from microsoft_agents.activity.activity_types import ActivityTypes
from microsoft_agents.activity.text_format_types import TextFormatTypes
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import TurnContext
from microsoft_agents.hosting.core.connector.client.connector_client import (
    ConversationsOperations,
)
from microsoft_agents.hosting.core.connector.teams import TeamsConnectorClient
from msgraph.generated.teams.item.channels.item.messages.item.replies.replies_request_builder import (
    RepliesRequestBuilder,
)
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.graph_service_client import GraphServiceClient
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

MCP_BOT_NAME = "MCP Bot"
DEFAULT_MEMBER_PAGE_SIZE = 100


class TeamsThread(BaseModel):
    thread_id: str = Field(
        description="Thread ID as a string in the format '1743086901347'"
    )
    title: str = Field(description="Message title")
    content: str = Field(description="Message content")


class TeamsMessage(BaseModel):
    thread_id: str = Field(
        description="Thread ID as a string in the format '1743086901347'"
    )
    message_id: str = Field(description="Message ID")
    content: str | None = Field(description="Message content")


class TeamsMember(BaseModel):
    id: str = Field(default="", description="Member ID used in mentions")
    name: str = Field(
        description="Member name used in mentions and user information cards"
    )
    email: str = Field(description="Member email")


class PagedTeamsMessages(BaseModel):
    cursor: str | None = Field(
        description="Cursor to retrieve the next page of messages."
    )
    limit: int = Field(description="Page limit, maximum number of items to retrieve")
    total: int = Field(description="Total items available for retrieval")
    items: list[TeamsMessage] = Field(description="List of channel messages or threads")


class PagedTeamsMembers(BaseModel):
    cursor: str | None = Field(
        description="Cursor to retrieve the next page of members."
    )
    limit: int = Field(description="Page limit, maximum number of members to retrieve")
    total: int = Field(description="Total members available for retrieval")
    items: list[TeamsMember] = Field(description="List of team members")


class TeamsClient:
    def __init__(
        self,
        adapter: CloudAdapter,
        graph_client: GraphServiceClient,
        teams_app_id: str,
        team_id: str,
        teams_channel_id: str,
    ):
        self.adapter = adapter
        self.graph_client = graph_client
        self.teams_app_id = teams_app_id
        self.team_id = team_id
        self.teams_channel_id = teams_channel_id
        self.service_url = None
        self.adapter.on_turn_error = self.on_turn_error

    def get_team_id(self):
        return self.team_id

    @staticmethod
    async def on_turn_error(context: TurnContext, error: Exception):
        LOGGER.error(
            "Error during turn",
            exc_info=(type(error), error, error.__traceback__),
        )
        # await context.send_activity("An error occurred in the bot, please try again later")

    def _create_continuation_activity(self) -> Activity:
        service_url = "https://smba.trafficmanager.net/emea/"
        if self.service_url is not None:
            service_url = self.service_url
        return Activity(
            type=ActivityTypes.conversation_update,
            service_url=service_url,
            from_property=ChannelAccount(id=self.teams_app_id, name=MCP_BOT_NAME),  # type: ignore
            channel_id="msteams",  # type: ignore
            conversation=ConversationAccount(
                id=self.teams_channel_id,
                is_group=True,
                conversation_type="channel",
                name="Teams channel",
            ),
        )

    async def _initialize(self):
        if not self.service_url:

            async def context_callback(context: TurnContext):
                self.service_url = context.activity.service_url

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=context_callback,
            )

    async def _get_mention_member(
        self, context: TurnContext, member_name: str | None
    ) -> TeamsMember | None:
        if member_name is None:
            return None

        cursor = None
        while True:
            members = await self._read_members_page(
                context, DEFAULT_MEMBER_PAGE_SIZE, cursor
            )
            for member in members.items:
                if member.name == member_name:
                    return member

            cursor = members.cursor
            if not cursor:
                return None

    async def _read_members_page(
        self,
        context: TurnContext,
        page_size: int,
        cursor: str | None = None,
    ) -> PagedTeamsMembers:
        teams_client = self._get_teams_connector_client(context)
        response = await teams_client.get_conversation_paged_member(
            self.teams_channel_id, page_size, cursor or ""
        )

        items = []
        for member in response.members:
            items.append(
                TeamsMember(
                    id=getattr(member, "id", None) or "",
                    name=getattr(member, "name", None) or "",
                    email=getattr(member, "email", None) or "",
                )
            )

        return PagedTeamsMembers(
            cursor=response.continuation_token,
            limit=page_size,
            total=len(items),
            items=items,
        )

    async def start_thread(
        self, title: str, content: str, member_name: str | None = None
    ) -> TeamsThread:
        """Start a new thread in a channel.

        Args:
            title: Thread title
            content: Initial thread content
            member_name: Member name to mention in content

        Returns:
            Created thread details including ID
        """
        try:
            await self._initialize()

            result = TeamsThread(title=title, content=content, thread_id="")

            async def start_thread_callback(context: TurnContext):
                mention_member = await self._get_mention_member(context, member_name)

                mentions = []
                if mention_member is not None:
                    result.content = (
                        f"# **{title}**\n<at>{mention_member.name}</at> {content}"
                    )
                    mention = Mention(
                        text=f"<at>{mention_member.name}</at>",
                        mentioned=ChannelAccount(
                            id=mention_member.id, name=mention_member.name
                        ),
                    )
                    mentions.append(mention)

                activity = Activity(
                    type=ActivityTypes.message,
                    from_property=ChannelAccount(
                        id=self.teams_app_id, name=MCP_BOT_NAME
                    ),  # type: ignore
                    channel_id="msteams",  # type: ignore
                    conversation=context.activity.conversation,
                    topic_name=title,
                    text=result.content,
                    text_format=TextFormatTypes.markdown,
                    entities=mentions,
                )

                responses = await self.adapter.send_activities(context, [activity])
                response = responses[0] if responses else None

                if response is None:
                    raise RuntimeError(
                        "Teams did not return a thread creation response"
                    )

                result.thread_id = response.id

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=start_thread_callback,
            )

            return result
        except Exception:
            LOGGER.exception("Error creating thread")
            raise

    @staticmethod
    def _get_conversation_operations(context: TurnContext) -> ConversationsOperations:
        # Hack to get the connector client and reply to an existing activity
        connector_client = context.turn_state["ConnectorClient"]
        return connector_client.conversations  # type: ignore

    @staticmethod
    def _get_teams_connector_client(context: TurnContext) -> TeamsConnectorClient:
        connector_client = context.turn_state.get("ConnectorClient")
        if isinstance(connector_client, TeamsConnectorClient):
            return connector_client
        raise TypeError("ConnectorClient is not a TeamsConnectorClient")

    async def update_thread(
        self, thread_id: str, content: str, member_name: str | None = None
    ) -> TeamsMessage:
        """Add a message to an existing thread, mentioning a user optionally.

        Args:
            thread_id: Thread ID to update
            content: Message content to add
            member_name: Member name to mention (optional)

        Returns:
            Updated thread details
        """
        try:
            await self._initialize()

            result = TeamsMessage(thread_id=thread_id, content=content, message_id="")

            async def update_thread_callback(context: TurnContext):
                mention_member = await self._get_mention_member(context, member_name)

                mentions = []
                if mention_member is not None:
                    result.content = f"<at>{mention_member.name}</at> {content}"
                    mention = Mention(
                        text=f"<at>{mention_member.name}</at>",
                        mentioned=ChannelAccount(
                            id=mention_member.id, name=mention_member.name
                        ),
                    )
                    mentions.append(mention)

                reply = Activity(
                    type=ActivityTypes.message,
                    text=result.content if result.content is not None else "",
                    from_property=ChannelAccount(
                        id=self.teams_app_id, name=MCP_BOT_NAME
                    ),  # type: ignore
                    conversation=ConversationAccount(id=thread_id),
                    entities=mentions,
                )
                #
                # Hack to get the connector client and reply to an existing activity
                #
                conversations = TeamsClient._get_conversation_operations(context)
                #
                # Hack to reply to conversation https://github.com/microsoft/botframework-sdk/issues/6626
                #
                conversation_id = (
                    f"{context.activity.conversation.id};messageid={thread_id}"  # pyright: ignore
                )
                response = await conversations.send_to_conversation(
                    conversation_id=conversation_id, body=reply
                )

                if response is None:
                    raise RuntimeError("Teams did not return a thread update response")

                result.message_id = response.id  # pyright: ignore

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=update_thread_callback,
            )

            return result
        except Exception:
            LOGGER.exception("Error updating thread")
            raise

    async def get_member_by_id(self, member_id: str) -> TeamsMember:
        try:
            await self._initialize()

            result = TeamsMember(id="", name="", email="")

            async def get_member_by_id_callback(context: TurnContext):
                member = await self._get_teams_connector_client(
                    context
                ).get_conversation_member(self.teams_channel_id, member_id)
                result.id = member.id
                result.name = member.name or ""
                result.email = member.email or ""

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=get_member_by_id_callback,
            )
            return result
        except Exception:
            LOGGER.exception("Error getting member by ID")
            raise

    async def read_threads(
        self, limit: int = 50, cursor: str | None = None
    ) -> PagedTeamsMessages:
        """Read all threads in configured teams channel.

        Args:
            cursor: The pagination cursor.

            limit: The pagination page size

        Returns:
            Paged team channel messages containing
        """
        try:
            query = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                top=limit
            )
            request = RequestConfiguration(query_parameters=query)
            if cursor is not None:
                response = (
                    await self.graph_client.teams.by_team_id(self.team_id)
                    .channels.by_channel_id(self.teams_channel_id)
                    .messages.with_url(cursor)
                    .get(request_configuration=request)
                )
            else:
                response = (
                    await self.graph_client.teams.by_team_id(self.team_id)
                    .channels.by_channel_id(self.teams_channel_id)
                    .messages.get(request_configuration=request)
                )

            items = []
            for message in getattr(response, "value", None) or []:
                message_id = getattr(message, "id", None) or ""
                body = getattr(message, "body", None)
                items.append(
                    TeamsMessage(
                        message_id=message_id,
                        content=getattr(body, "content", None),
                        thread_id=message_id,
                    )
                )

            total = getattr(response, "odata_count", None)
            result = PagedTeamsMessages(
                cursor=getattr(response, "odata_next_link", None),
                limit=limit,
                total=total if total is not None else len(items),
                items=items,
            )

            return result
        except Exception:
            LOGGER.exception("Error reading threads")
            raise

    async def read_thread_replies(
        self, thread_id: str, limit: int = 50, cursor: str | None = None
    ) -> PagedTeamsMessages:
        """Read all replies in a thread.

        Args:
            thread_id: Thread ID to read
            cursor: The pagination cursor
            limit: The pagination page size

        Returns:
            List of thread messages
        """
        try:
            params = RepliesRequestBuilder.RepliesRequestBuilderGetQueryParameters(
                top=limit
            )
            request = RequestConfiguration(query_parameters=params)

            if cursor is not None:
                replies = (
                    await self.graph_client.teams.by_team_id(self.team_id)
                    .channels.by_channel_id(self.teams_channel_id)
                    .messages.by_chat_message_id(thread_id)
                    .replies.with_url(cursor)
                    .get(request_configuration=request)
                )
            else:
                replies = (
                    await self.graph_client.teams.by_team_id(self.team_id)
                    .channels.by_channel_id(self.teams_channel_id)
                    .messages.by_chat_message_id(thread_id)
                    .replies.get(request_configuration=request)
                )

            items = []
            for reply in getattr(replies, "value", None) or []:
                body = getattr(reply, "body", None)
                items.append(
                    TeamsMessage(
                        message_id=getattr(reply, "id", None) or "",
                        content=getattr(body, "content", None),
                        thread_id=getattr(reply, "reply_to_id", None) or thread_id,
                    )
                )

            total = getattr(replies, "odata_count", None)
            result = PagedTeamsMessages(
                cursor=getattr(replies, "odata_next_link", None),
                limit=limit,
                total=total if total is not None else len(items),
                items=items,
            )

            return result
        except Exception:
            LOGGER.exception("Error reading thread replies")
            raise

    async def list_members(
        self, page_size: int = DEFAULT_MEMBER_PAGE_SIZE
    ) -> list[TeamsMember]:
        """List all members in the configured team.

        Args:
            page_size: Number of members to retrieve per request.

        Returns:
            List of team member details
        """
        try:
            await self._initialize()
            result = []

            async def list_members_callback(context: TurnContext):
                cursor = None
                while True:
                    members = await self._read_members_page(context, page_size, cursor)
                    result.extend(members.items)

                    cursor = members.cursor
                    if not cursor:
                        return

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=list_members_callback,
            )
            return result
        except Exception:
            LOGGER.exception("Error listing members")
            raise

    async def get_member_by_name(self, name: str) -> TeamsMember | None:
        members = await self.list_members()
        for member in members:
            if member.name == name:
                return member
        return None
