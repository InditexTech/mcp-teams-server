import logging
from typing import List

from botframework.connector.aio.operations_async import ConversationsOperations
from msgraph.generated.models.chat_message import ChatMessage
from msgraph.generated.teams.item.channels.item.messages.item.chat_message_item_request_builder import \
    ChatMessageItemRequestBuilder
from msgraph.generated.teams.item.channels.item.messages.item.replies.replies_request_builder import \
    RepliesRequestBuilder
from pydantic import BaseModel
from uuid import UUID

from botbuilder.core import TurnContext, BotAdapter
from botbuilder.core.teams import TeamsInfo
from botbuilder.integration.aiohttp import CloudAdapter
from botbuilder.schema import (
    Activity,
    ActivityTypes,
    ConversationReference, ChannelAccount, ConversationAccount, Mention, MessageReaction, MessageReactionTypes,
)
from botbuilder.schema.teams import TeamsChannelAccount
from msgraph import GraphServiceClient
from msgraph.generated.models.app_role_assignment import AppRoleAssignment
from msgraph.generated.teams.item.channels.item.messages.messages_request_builder import MessagesRequestBuilder
from msrest.exceptions import HttpOperationError

LOGGER = logging.getLogger(__name__)


class TeamsThread(BaseModel):
    thread_id: str
    title: str
    content: str


class TeamsMessage(BaseModel):
    thread_id: str
    message_id: str
    content: str


class TeamsMember(BaseModel):
    member_id: str
    name: str
    email: str


class PagedTeamsMessages(BaseModel):
    offset: int
    limit: int
    total: int
    items: List[TeamsMessage]


class TeamsClient:
    #
    # https://learn.microsoft.com/en-us/graph/permissions-reference#resource-specific-consent-rsc-permissions
    # ChannelMessage.Read.Group
    CHANNEL_MESSAGE_READ_GROUP: str = "19103a54-c397-4bcd-be5a-ef111e0406fa"

    def __init__(self, adapter: CloudAdapter, graph_client: GraphServiceClient, teams_app_id: str, team_id: str,
                 teams_channel_id: str):
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
        LOGGER.error(f"Error {error}")
        # await context.send_activity("An error occurred in the bot, please try again later")
        pass

    def _create_conversation_reference(self) -> ConversationReference:
        service_url = "https://smba.trafficmanager.net/emea/"
        if self.service_url is not None:
            service_url = self.service_url
        return ConversationReference(
            bot=TeamsChannelAccount(id=self.teams_app_id, name="MCP Bot"),
            channel_id=self.teams_channel_id,
            service_url=service_url,
            conversation=ConversationAccount(id=self.teams_channel_id, is_group=True, conversation_type="channel",
                                             name="Teams channel")
        )

    def _initialize(self) -> str:
        if not self.service_url:
            def context_callback(context: TurnContext):
                self.service_url = context.activity.service_url

            self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                               reference=self._create_conversation_reference(),
                                               callback=context_callback)
        return self.service_url

    async def start_thread(
            self, title: str, content: str
    ) -> TeamsThread:
        """Start a new thread in a channel.

        Args:
            title: Thread title
            content: Initial thread content

        Returns:
            Created thread details including ID
        """
        try:
            self._initialize()

            result = TeamsThread(
                title=title,
                content=content,
                thread_id=""
            )

            async def start_thread_callback(context: TurnContext):
                response = await context.send_activity(activity_or_text=Activity(
                    type=ActivityTypes.message,
                    topic_name=title,
                    text=content
                ))
                if response is not None:
                    result.thread_id = response.id

            await self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                                     reference=self._create_conversation_reference(),
                                                     callback=start_thread_callback)

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error creating thread: {str(e)}")
            raise

    @staticmethod
    def _get_conversation_operations(context: TurnContext) -> ConversationsOperations:
        # Hack to get the connector client and reply to an existing activity
        connector_client = context.turn_state[BotAdapter.BOT_CONNECTOR_CLIENT_KEY]
        return connector_client.conversations

    async def update_thread(
            self, thread_id: str, content: str
    ) -> TeamsMessage:
        """Add a message to an existing thread.

        Args:
            thread_id: Thread ID to update
            content: Message content to add

        Returns:
            Updated thread details
        """
        try:
            self._initialize()

            result = TeamsMessage(
                thread_id=thread_id,
                content=content,
                message_id=""
            )

            async def update_thread_callback(context: TurnContext):
                reply = Activity(
                    type=ActivityTypes.message,
                    text=content,
                    from_property=TeamsChannelAccount(id=self.teams_app_id, name="MCP Bot"),
                    conversation=ConversationAccount(id=thread_id)
                )
                #
                # Hack to get the connector client and reply to an existing activity
                #
                conversations = TeamsClient._get_conversation_operations(context)
                #
                # Hack to reply to conversation https://github.com/microsoft/botframework-sdk/issues/6626
                #
                conversation_id = f"{context.activity.conversation.id};messageid={thread_id}"
                response = await conversations.send_to_conversation(conversation_id=conversation_id, activity=reply)

                if response is not None:
                    result.message_id = response.id

            await self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                                     reference=self._create_conversation_reference(),
                                                     callback=update_thread_callback)

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error updating thread: {str(e)}")
            raise

    async def mention_user(
            self,
            thread_id: str,
            user_id: str,
            content: str
    ) -> TeamsMessage:
        """Mention a user in a thread message.

        Args:
            thread_id: Thread ID to add mention
            user_id: ID of user to mention
            content: Message content

        Returns:
            Message details including IDs
        """
        try:
            self._initialize()

            result = TeamsMessage(
                thread_id=thread_id,
                content=content,
                message_id=""
            )

            async def mention_user_callback(context: TurnContext):
                member = await TeamsInfo.get_team_member(context, self.team_id, user_id)

                mention = Mention(text=f"<at>{member.name}</at>", type="mention",
                                  mentioned=ChannelAccount(id=user_id, name=member.name))

                reply = Activity(
                    type=ActivityTypes.message,
                    text=f'<at>{member.name}</at> {content}',
                    conversation=ConversationAccount(id=thread_id),
                    entities=[mention]
                )

                conversations = TeamsClient._get_conversation_operations(context)
                conversation_id = f"{context.activity.conversation.id};messageid={thread_id}"
                response = await conversations.send_to_conversation(conversation_id=conversation_id, activity=reply)

                if response is not None:
                    result.message_id = response.id

            await self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                                     reference=self._create_conversation_reference(),
                                                     callback=mention_user_callback)

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error mentioning user: {str(e)}")
            raise

    async def _grant_channel_group_read(self) -> AppRoleAssignment:
        # https://learn.microsoft.com/en-us/graph/permissions-grant-via-msgraph?tabs=python&pivots=grant-application-permissions
        request = AppRoleAssignment(
            principal_id=UUID(self.teams_app_id),
            resource_id=UUID(self.team_id),
            app_role_id=UUID(TeamsClient.CHANNEL_MESSAGE_READ_GROUP)
        )
        result = await self.graph_client.service_principals.by_service_principal_id(
            self.teams_app_id).app_role_assigned_to.post(request)
        LOGGER.info(f"Granted app role {result}")
        return result

    async def read_threads(self, offset: int, limit: int = 50) -> PagedTeamsMessages:
        """Read all threads in configured teams channel.
        
        Args:
            offset: The pagination offset or first result to return.
            
            limit: The pagination page size
        
        Returns:
            Paged teams messages
        """
        try:
            query = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(skip=offset, top=limit)
            request = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(query_parameters=query)
            response = await self.graph_client.teams.by_team_id(self.team_id).channels.by_channel_id(
                self.teams_channel_id).messages.get(request_configuration=request)

            result = PagedTeamsMessages(offset=offset, limit=limit, total=response.odata_count, items=[])
            for message in response.value:
                result.items.append(
                    TeamsMessage(message_id=message.id, content=message.body.content, thread_id=message.id))

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
            raise

    async def read_thread_replies(
            self, thread_id: str, offset: int, limit: int = 100
    ) -> PagedTeamsMessages:
        """Read all replies in a thread.

        Args:
            thread_id: Thread ID to read
            offset: The pagination offset
            limit: The pagination page size

        Returns:
            List of thread messages
        """
        try:
            params = RepliesRequestBuilder.RepliesRequestBuilderGetQueryParameters()
            request = RepliesRequestBuilder.RepliesRequestBuilderGetRequestConfiguration(
                query_parameters=params)

            replies = await self.graph_client.teams.by_team_id(self.team_id).channels.by_channel_id(
                self.teams_channel_id).messages.by_chat_message_id(thread_id).replies.get(request_configuration=request)

            result = PagedTeamsMessages(offset=offset, limit=limit, total=replies.odata_count, items=[])

            if replies is not None:
                for reply in replies.value:
                    result.items.append(
                        TeamsMessage(message_id=reply.id, content=reply.body.content, thread_id=reply.reply_to_id))

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
            raise

    async def read_message(self, message_id: str) -> ChatMessage:
        try:
            query = ChatMessageItemRequestBuilder.ChatMessageItemRequestBuilderGetQueryParameters()
            request = ChatMessageItemRequestBuilder.ChatMessageItemRequestBuilderGetRequestConfiguration(
                query_parameters=query)
            response = await self.graph_client.teams.by_team_id(self.team_id).channels.by_channel_id(
                self.teams_channel_id).messages.by_chat_message_id(chat_message_id=message_id).get(
                request_configuration=request)
            return response
        except HttpOperationError as e:
            LOGGER.error(f"Error reading thread: {str(e)}")
            raise

    async def list_members(self) -> List[TeamsMember]:
        """List all members in the configured team.

        Returns:
            List of team member details
        """
        try:
            self._initialize()
            result = []

            async def list_members_callback(context: TurnContext):
                members = await TeamsInfo.get_team_members(context, self.team_id)
                for member in members:
                    result.append(TeamsMember(member_id=member.id, name=member.name, email=member.email))

            await self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                                     reference=self._create_conversation_reference(),
                                                     callback=list_members_callback)
            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error listing members: {str(e)}")
            raise

    async def add_reaction(
            self, message_id: str, reaction: str
    ) -> TeamsMessage:
        """Add a reaction to a message.

        Args:
            message_id: Message ID to react to
            reaction: Reaction emoji name

        Returns:
            Reaction details
        """
        try:
            self._initialize()

            result = TeamsMessage(
                message_id=message_id,
                thread_id="",
                content=""
            )

            message = await self.read_message(message_id=message_id)

            async def add_reaction_callback(context: TurnContext):
                activity = Activity(type=ActivityTypes.message,
                                    id=message_id,
                                    text=message.body.content,
                                    reactions_added=[MessageReaction(type=MessageReactionTypes.like)])
                response = await context.update_activity(activity=activity)
                pass

            await self.adapter.continue_conversation(bot_app_id=self.teams_app_id,
                                                     reference=self._create_conversation_reference(),
                                                     callback=add_reaction_callback)

            return result
        except HttpOperationError as e:
            LOGGER.error(f"Error adding reaction: {str(e)}")
            raise
