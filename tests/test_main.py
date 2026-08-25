# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import os
import sys
from unittest.mock import patch

import pytest

import mcp_teams_server
from mcp_teams_server import MAX_MEMBER_PAGE_SIZE, MAX_THREAD_PAGE_SIZE, main


def test_main_should_exit_error_on_missing_env_vars():
    # Unset environment
    for var in mcp_teams_server.REQUIRED_ENV_VARS:
        os.environ.pop(var, None)

    test_args = ["main"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exit_code:
            main()

    assert exit_code.type is SystemExit
    assert exit_code.value.code == 1


def test_main_should_pass_cli_transport_as_string():
    test_args = ["main", "--transport", "sse"]
    env_vars = {var: "value" for var in mcp_teams_server.REQUIRED_ENV_VARS}

    with patch.dict(os.environ, env_vars, clear=True):
        with patch.object(sys, "argv", test_args):
            with patch.object(mcp_teams_server.mcp, "run") as run:
                main()

    run.assert_called_once_with(transport="sse")


def test_main_should_pass_env_transport_as_string():
    test_args = ["main"]
    env_vars = {var: "value" for var in mcp_teams_server.REQUIRED_ENV_VARS}
    env_vars["MCP_TRANSPORT"] = "sse"

    with patch.dict(os.environ, env_vars, clear=True):
        with patch.object(sys, "argv", test_args):
            with patch.object(mcp_teams_server.mcp, "run") as run:
                main()

    run.assert_called_once_with(transport="sse")


@pytest.mark.asyncio
async def test_list_tools():
    tools = await mcp_teams_server.mcp.list_tools()

    assert tools is not None


@pytest.mark.asyncio
async def test_tool_schemas_expose_input_validation_constraints():
    tools = await mcp_teams_server.mcp.list_tools()
    schemas = {tool.name: tool.inputSchema for tool in tools}

    start_thread_properties = schemas["start_thread"]["properties"]
    assert start_thread_properties["title"]["minLength"] == 1
    assert start_thread_properties["content"]["minLength"] == 1
    assert start_thread_properties["member_name"]["anyOf"][0]["minLength"] == 1

    update_thread_properties = schemas["update_thread"]["properties"]
    assert update_thread_properties["thread_id"]["minLength"] == 1
    assert update_thread_properties["content"]["minLength"] == 1
    assert update_thread_properties["member_name"]["anyOf"][0]["minLength"] == 1

    read_thread_properties = schemas["read_thread"]["properties"]
    assert read_thread_properties["thread_id"]["minLength"] == 1

    list_threads_properties = schemas["list_threads"]["properties"]
    assert list_threads_properties["limit"]["minimum"] == 1
    assert list_threads_properties["limit"]["maximum"] == MAX_THREAD_PAGE_SIZE
    assert list_threads_properties["cursor"]["anyOf"][0]["minLength"] == 1

    get_member_properties = schemas["get_member_by_name"]["properties"]
    assert get_member_properties["name"]["minLength"] == 1

    list_members_properties = schemas["list_members"]["properties"]
    assert list_members_properties["page_size"]["minimum"] == 1
    assert list_members_properties["page_size"]["maximum"] == MAX_MEMBER_PAGE_SIZE
