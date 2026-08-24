# SPDX-FileCopyrightText: 2025 INDUSTRIA DE DISEÑO TEXTIL, S.A. (INDITEX, S.A.)
# SPDX-License-Identifier: Apache-2.0
import os
import sys
from unittest.mock import patch

import pytest

import mcp_teams_server
from mcp_teams_server import main


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
