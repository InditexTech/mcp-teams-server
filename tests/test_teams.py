import pytest
from azure.identity.aio import ClientSecretCredential

from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from msgraph import GraphServiceClient

from mcp_teams_server.config import BotConfiguration
from mcp_teams_server.teams import TeamsClient

import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

LOGGER = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.fixture()
def setup_teams_client() -> TeamsClient:
    # Cloud adapter
    config = BotConfiguration()
    adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(config, logger=LOGGER))

    # Graph client
    credentials = ClientSecretCredential(
        config.APP_TENANTID,
        config.GRAPH_CLIENT_ID,
        config.GRAPH_CLIENT_SECRET
    )
    scopes = ['https://graph.microsoft.com/.default']
    graph_client = GraphServiceClient(credentials=credentials, scopes=scopes)

    return TeamsClient(adapter, graph_client, config.APP_ID, config.TEAM_ID, config.TEAMS_CHANNEL_ID)

@pytest.fixture()
def thread_id() -> str:
    return "1742812462884"

@pytest.fixture()
def message_id() -> str:
    return "1742812462884"

@pytest.fixture()
def user_id() -> str:
    return "29:1Ikp2uml8KHyXMGToEGWznopw1RLAu1IyyNa8sOR7BGR3O2VkeVTk5n9N0c_tv-mAA0Nogcp-NJbFsDybDsG7TA"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_start_thread(setup_teams_client):
    LOGGER.info(f'test_start_thread in team: {setup_teams_client.team_id} and channel {setup_teams_client.teams_channel_id}')
    result = await setup_teams_client.start_thread("First thread", "First thread content")
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_threads(setup_teams_client):
    result = await setup_teams_client.read_threads(0, 50)
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_thread(setup_teams_client, thread_id):
    result = await setup_teams_client.update_thread(thread_id, "Thread updated content")
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_mention_user(setup_teams_client, thread_id, user_id):
    result = await setup_teams_client.mention_user(thread_id, user_id, "User mentioned")
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_add_reaction(setup_teams_client, message_id):
    result = await setup_teams_client.add_reaction(message_id, "")
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_thread_replies(setup_teams_client, thread_id):
    result = await setup_teams_client.read_thread_replies(thread_id, 0, 50)
    print(f'Result {result}\n')
    assert result is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_members(setup_teams_client):
    result = await setup_teams_client.list_members()
    print(f'Result {result}\n')
    assert result is not None



