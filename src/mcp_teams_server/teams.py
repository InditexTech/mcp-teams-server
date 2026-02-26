# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import logging

from microsoft_agents.hosting.core import TurnContext
from microsoft_agents.hosting.core.connector.client.connector_client import ConversationsOperations
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.teams import TeamsInfo
from microsoft_agents.activity import (
    Activity,
    ChannelAccount,
    ConversationAccount
)
from microsoft_agents.activity.activity_types import ActivityTypes
from microsoft_agents.activity import Mention
from microsoft_agents.activity.text_format_types import TextFormatTypes
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.teams.item.channels.item.messages.item.chat_message_item_request_builder import (
    ChatMessageItemRequestBuilder,
)
from msgraph.generated.teams.item.channels.item.messages.item.replies.replies_request_builder import (
    RepliesRequestBuilder,
)
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.graph_service_client import GraphServiceClient
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)


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
    content: str = Field(description="Message content")


class TeamsMember(BaseModel):
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
        LOGGER.error(f"Error {str(error)}")
        # await context.send_activity("An error occurred in the bot, please try again later")

    def _create_continuation_activity(self) -> Activity:
        service_url = "https://smba.trafficmanager.net/emea/"
        if self.service_url is not None:
            service_url = self.service_url
        return Activity(
            type=ActivityTypes.conversation_update,
            service_url=service_url,
            channel_id=self.teams_channel_id,
            from_property=ChannelAccount(id=self.teams_app_id, name="MCP Bot"),
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
                mention_member = None
                if member_name is not None:
                    continuation_token = None
                    members = await TeamsInfo.get_paged_team_members(context, self.team_id, 10, continuation_token)
                    for member in members.members:
                        if member.name == member_name:
                            mention_member = member

                mentions = []
                if mention_member is not None:
                    result.content = (
                        f"# **{title}**\n<at>{mention_member.name}</at> {content}"
                    )
                    mention = Mention(
                        text=f"<at>{mention_member.name}</at>",
                        type="mention",
                        mentioned=ChannelAccount(
                            id=mention_member.id, name=mention_member.name
                        ),
                    )
                    mentions.append(mention)

                response = await context.send_activity(
                    activity_or_text=Activity(
                        type=ActivityTypes.message,
                        topic_name=title,
                        text=result.content,
                        text_format=TextFormatTypes.markdown,
                        entities=mentions,
                    )
                )
                if response is not None:
                    result.thread_id = response.id

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=start_thread_callback,
            )

            return result
        except Exception as e:
            LOGGER.error(f"Error creating thread: {str(e)}")
            raise

    @staticmethod
    def _get_conversation_operations(context: TurnContext) -> ConversationsOperations:
        # Hack to get the connector client and reply to an existing activity
        connector_client = context.turn_state["ConnectorClient"]
        return connector_client.conversations  # pyright: ignore

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
                mention_member = None
                if member_name is not None:
                    continuation_token = None
                    members = await TeamsInfo.get_paged_team_members(context, self.team_id, 10, continuation_token)
                    for member in members.members:
                        if member.name == member_name:
                            mention_member = member

                mentions = []
                if mention_member is not None:
                    result.content = f"<at>{mention_member.name}</at> {content}"
                    mention = Mention(
                        text=f"<at>{mention_member.name}</at>",
                        type="mention",
                        mentioned=ChannelAccount(
                            id=mention_member.id, name=mention_member.name
                        ),
                    )
                    mentions.append(mention)

                reply = Activity(
                    type=ActivityTypes.message,
                    text=result.content,
                    from_property=ChannelAccount(
                        id=self.teams_app_id, name="MCP Bot"
                    ),
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

                if response is not None:
                    result.message_id = response.id  # pyright: ignore

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=update_thread_callback,
            )

            return result
        except Exception as e:
            LOGGER.error(f"Error updating thread: {str(e)}")
            raise

    async def get_member_by_id(self, member_id: str) -> TeamsMember:
        try:
            await self._initialize()

            result = TeamsMember(name="", email="")

            async def get_member_by_id_callback(context: TurnContext):
                member = await TeamsInfo.get_team_member(
                    context, self.team_id, member_id
                )
                result.name = member.name
                result.email = member.email

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=get_member_by_id_callback,
            )
            return result
        except Exception as e:
            LOGGER.error(f"Error updating thread: {str(e)}")
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

            result = PagedTeamsMessages(
                cursor=response.odata_next_link,  # pyright: ignore
                limit=limit,
                total=response.odata_count,  # pyright: ignore
                items=[],
            )
            if response.value is not None:  # pyright: ignore
                for message in response.value:  # pyright: ignore
                    result.items.append(
                        TeamsMessage(
                            message_id=message.id,  # pyright: ignore
                            content=message.body.content,  # pyright: ignore
                            thread_id=message.id,  # pyright: ignore
                        )
                    )

            return result
        except Exception as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
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

            result = PagedTeamsMessages(
                cursor=cursor,
                limit=limit,
                total=replies.odata_count,  # pyright: ignore
                items=[],
            )

            if replies is not None and replies.value is not None:
                for reply in replies.value:
                    result.items.append(
                        TeamsMessage(
                            message_id=reply.id,  # pyright: ignore
                            content=reply.body.content,  # pyright: ignore
                            thread_id=reply.reply_to_id,  # pyright: ignore
                        )
                    )

            return result
        except Exception as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
            raise

    async def read_message(self, message_id: str) -> ChatMessage | None:
        try:
            query = ChatMessageItemRequestBuilder.ChatMessageItemRequestBuilderGetQueryParameters()
            request = RequestConfiguration(query_parameters=query)
            response = (
                await self.graph_client.teams.by_team_id(self.team_id)
                .channels.by_channel_id(self.teams_channel_id)
                .messages.by_chat_message_id(chat_message_id=message_id)
                .get(request_configuration=request)
            )
            return response
        except Exception as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
            raise

    async def list_members(self) -> list[TeamsMember]:
        """List all members in the configured team.

        Returns:
            List of team member details
        """
        try:
            await self._initialize()
            result = []

            async def list_members_callback(context: TurnContext):
                continuation_token = None
                members = await TeamsInfo.get_paged_team_members(context, self.team_id, 10,continuation_token)
                for member in members.members:
                    result.append(TeamsMember(name=member.name, email=member.email))

            await self.adapter.continue_conversation(
                agent_app_id=self.teams_app_id,
                continuation_activity=self._create_continuation_activity(),
                callback=list_members_callback,
            )
            return result
        except Exception as e:
            LOGGER.error(f"Error listing members: {str(e)}")
            raise

    async def get_member_by_name(self, name: str) -> TeamsMember | None:
        members = await self.list_members()
        for member in members:
            if member.name == name:
                return member
        return None
