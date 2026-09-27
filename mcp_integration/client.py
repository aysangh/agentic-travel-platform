from typing import cast

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection

from config import config


mcp_client = MultiServerMCPClient(
    cast(
        dict[str, Connection],
        {
            "travel": {
                "transport": "streamable_http",
                "url": config.mcp_server_url,
            }
        },
    )
)