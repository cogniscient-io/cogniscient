#!/usr/bin/env python3
"""
Test script to verify the MCP client implementation.
"""

import asyncio
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.mcp.client_manager import MCPConnection
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp import Implementation


async def test_client_connection():
    """Test basic MCP client connection."""
    print("Testing MCP client connection...")
    
    # Try to connect to a test server (this will likely fail if no server is running)
    # but this is just to test that the client classes work properly
    server_url = "http://localhost:3000"  # Default example server
    
    connection = MCPConnection(server_url)
    
    try:
        print("Attempting to create client session...")
        client, connection_obj = await connection._create_client_session(server_url)
        
        print("Client session created successfully")
        print(f"Client type: {type(client)}")
        
        # Test basic methods
        print("Testing list_tools method...")
        tools = await client.list_tools()
        print(f"Tools: {tools}")
        
        print("Testing that get_tool exists and is callable...")
        print(f"Has get_tool: {hasattr(client, 'get_tool')}")
        print(f"get_tool method: {getattr(client, 'get_tool', 'NOT FOUND')}")
        
        # Test calling list_tools instead (since get_tool was removed)
        try:
            result = await client.list_tools()
            print(f"list_tools result: {result}")
        except Exception as e:
            print(f"list_tools failed: {e}")
        
        await connection.disconnect()
        print("Test completed successfully")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_client_connection())