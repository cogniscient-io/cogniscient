"""
MCP Client Manager for managing multiple MCP server connections.

This module implements the MCPClientManager class which coordinates
multiple MCP client connections to various servers.
The manager focuses on establishing and managing connections to different MCP servers,
while the MCPClient class performs actual operations on the established sessions.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import MCPConfig, ToolResult
from gcs_kernel.mcp.server_registry import MCPServerRegistry, MCPServerInfo
from datetime import datetime
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp import Implementation


class MCPConnection:
    """
    A connection manager for MCP servers that handles the stream lifecycle.
    """

    def __init__(self, server_url: str, headers: Optional[Dict[str, str]] = None):
        self.server_url = server_url
        self.headers = headers or {}

        # Ensure required headers
        if 'Accept' not in self.headers:
            self.headers['Accept'] = 'text/event-stream'
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'

        self.session = None
        self.connected = False
        self._connection_task = None

    async def connect(self):
        """
        Establish connection to the MCP server using a background task approach.
        """
        # Create a background task that maintains the connection
        async def connection_loop():
            async with streamablehttp_client(url=self.server_url, headers=self.headers) as (read_stream, write_stream, get_session_id):
                # Create and use the ClientSession as an async context manager
                async with ClientSession(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    client_info=Implementation(
                        name="gcs-kernel-mcp-client",
                        version="1.0.0"
                    )
                ) as session:
                    # Initialize the session (the MCP protocol handshake)
                    await session.initialize()

                    # Store the session for use by the client
                    self.session = session
                    self.connected = True

                    # Keep the connection alive until cancelled
                    try:
                        import anyio
                        await anyio.sleep(float('inf'))  # Sleep indefinitely
                    except anyio.get_cancelled_exc_class():
                        # Expected when cancelling
                        pass

        # Run the connection loop in background
        self._connection_task = asyncio.create_task(connection_loop())

        # Wait a bit to allow connection to establish
        await asyncio.sleep(0.2)

        if not self.connected:
            # If connection failed, cancel the task and raise an error
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
            raise Exception(f"Failed to connect to {self.server_url}")

        # Return client that works with the established session
        return MCPClient(self.session, self.server_url)

    async def disconnect(self):
        """
        Close the connection to the MCP server.
        """
        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling


class MCPClientManager:
    """
    Manages multiple MCP client connections to various servers.
    """

    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP client manager.

        Args:
            config: Base configuration (used for fallback if global settings not available)
        """
        self.config = config
        # Changed to store client and connection pairs
        self.clients: Dict[str, Dict[str, Any]] = {}

        # Use the config's runtime data directory and registry filename if available
        runtime_data_directory = getattr(self.config, 'runtime_data_directory', None)
        registry_filename = getattr(self.config, 'server_registry_filename', None)

        # Get registry settings from config if provided, otherwise from global config
        if runtime_data_directory is not None:
            self.server_registry = MCPServerRegistry(
                runtime_data_directory=runtime_data_directory,
                registry_filename=registry_filename
            )
        else:
            from common.settings import settings
            self.server_registry = MCPServerRegistry(
                runtime_data_directory=settings.mcp_runtime_data_directory,
                registry_filename=settings.mcp_server_registry_filename
            )
        self.logger = None  # Will be set by kernel
        self.initialized = False

        # Notification handlers for different types of server notifications
        self.notification_handlers: Dict[str, List[Callable]] = {
            "tool_added": [],
            "tool_removed": [],
            "tool_updated": [],
            "server_status_change": []
        }
        
        # Reference to the tool discovery service (will be set by kernel)
        self._tool_discovery_service = None

    async def initialize(self, connect_to_registered_servers=True):
        """Initialize the client manager and optionally connect to previously registered servers."""
        if self.logger:
            self.logger.debug("Starting MCP client manager initialization")

        self.initialized = True

        # Optionally load and connect to previously registered external servers
        # But do it in the background to not block initialization
        if connect_to_registered_servers:
            asyncio.create_task(self._connect_to_registered_servers())

    async def _connect_to_registered_servers(self):
        """Connect to registered servers in the background."""
        start_time = time.time()

        if self.logger:
            self.logger.debug("Starting background connection to registered servers")

        # Load and connect to previously registered external servers
        servers = self.server_registry.get_all_servers()

        if self.logger:
            self.logger.debug(f"Found {len(servers)} servers in registry, connecting to active ones...")

        for server_info in servers:
            if server_info.status == "active":
                try:
                    if self.logger:
                        self.logger.debug(f"Attempting to connect to server: {server_info.name} at {server_info.server_url}")

                    connect_start_time = time.time()
                    # Connect to the server
                    success = await self.connect_to_server(
                        server_info.server_url,
                        server_info.name,
                        description=server_info.description
                    )

                    connect_elapsed = time.time() - connect_start_time
                    if success and self.logger:
                        self.logger.info(f"Successfully connected to server: {server_info.name} at {server_info.server_url} (elapsed: {connect_elapsed:.2f}s)")
                        
                        # Get the updated server info to access capabilities
                        updated_server_info = self.server_registry.get_server(server_info.server_id)
                        if updated_server_info and updated_server_info.capabilities:
                            # Emit a tools_discovered event for the reconnected server
                            await self._notify_tool_discovered_event("tools_discovered", 
                                                                     updated_server_info.server_id, 
                                                                     updated_server_info.capabilities, 
                                                                     updated_server_info.server_url)
                    elif self.logger:
                        self.logger.warning(f"Failed to connect to server: {server_info.name} at {server_info.server_url} (elapsed: {connect_elapsed:.2f}s)")
                        self.server_registry.update_server_status(server_info.server_id, "disconnected")
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error initializing server {server_info.name}: {e}")
                    self.server_registry.update_server_status(server_info.server_id, "error")

        if self.logger:
            total_elapsed = time.time() - start_time
            self.logger.debug(f"Background connection to registered servers completed (elapsed: {total_elapsed:.2f}s)")

    async def shutdown(self):
        """Shutdown all managed clients."""
        for client_data in self.clients.values():
            if isinstance(client_data, dict) and 'connection' in client_data:
                await client_data['connection'].disconnect()
        self.clients.clear()
        self.initialized = False

    async def _create_client_session(self, server_url: str, headers: Optional[Dict[str, str]] = None):
        """
        Create an MCP client session connected to the specified server URL.

        Args:
            server_url: The URL of the MCP server to connect to
            headers: Optional headers to include in the HTTP requests

        Returns:
            tuple: (MCPClient, connection) - The client and connection manager
        """
        connection = MCPConnection(server_url, headers)
        client = await connection.connect()
        return client, connection

    async def connect_to_server(self, server_url: str, server_name: str = None, description: str = None) -> bool:
        """
        Connect to an MCP server (primary or external) using the official Streamable HTTP protocol.

        Args:
            server_url: URL of the server to connect to
            server_name: Optional name for the server
            description: Optional description for the server

        Returns:
            True if connection was successful, False otherwise
        """
        if not self.initialized:
            await self.initialize()

        # Create a unique ID for this server connection
        import hashlib
        server_id = hashlib.md5(server_url.encode()).hexdigest()

        # Create and establish connection using the connection manager utilities
        try:
            client, connection = await self._create_client_session(server_url)
            if client is None:
                if self.logger:
                    self.logger.error(f"Failed to create client session for {server_url}")
                return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create client session for {server_url}: {e}")
            return False

        # Set logger
        client.logger = self.logger

        # Test the connection using the official MCP protocol with timeout
        try:
            # Test connection by listing tools
            tools_response = await asyncio.wait_for(
                client.list_tools(),
                timeout=getattr(self.config, 'connection_timeout', 30)
            )

            if tools_response is not None:
                connection_result = {"success": True, "message": "Connected to server successfully"}
            else:
                connection_result = {"success": False, "message": "Failed to get tools from server"}
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.error(f"Connection test to {server_url} timed out")
            connection_result = {"success": False, "message": "Connection test timed out"}

        if connection_result["success"]:
            # Add to our client registry with the connection for later disconnection
            self.clients[server_id] = {'client': client, 'connection': connection}

            # If name not provided, use URL
            if not server_name:
                server_name = server_url
            if not description:
                description = f"MCP server at {server_url}"

            # Update server info with capabilities discovered from the server
            try:
                # Get tools to determine capabilities
                tools_response = await client.list_tools()
                if tools_response and "tools" in tools_response:
                    capabilities = [tool.get("name", "") if isinstance(tool, dict) else str(tool) for tool in tools_response["tools"]]
                else:
                    capabilities = []
            except Exception:
                capabilities = []  # If we can't get tools, start with empty list

            # Create and register server info
            server_info = MCPServerInfo(
                server_id=server_id,
                server_url=server_url,
                name=server_name,
                description=description,
                capabilities=capabilities,
                last_connected=datetime.now(),
                status="active"
            )

            # Add to registry
            success = self.server_registry.add_server(server_info)
            if success and self.logger:
                self.logger.info(f"Registered server connection: {server_name}")

            # Emit a tools_discovered event to signal that tools from this server should be registered
            if self.logger:
                self.logger.info(f"Emitting tools_discovered event for server {server_id} with capabilities: {capabilities}")
            await self._notify_tool_discovered_event("tools_discovered", server_id, capabilities, server_url)

            return True
        else:
            await connection.disconnect()
            if self.logger:
                self.logger.error(f"Failed to connect to server {server_url}: {connection_result['message']}")
            return False

    async def disconnect_from_server(self, server_id: str) -> bool:
        """
        Disconnect from an MCP server.

        Args:
            server_id: ID of the server to disconnect from

        Returns:
            True if disconnection was successful, False otherwise
        """
        if server_id in self.clients:
            client_data = self.clients[server_id]
            if isinstance(client_data, dict) and 'connection' in client_data:
                await client_data['connection'].disconnect()
            del self.clients[server_id]

            # Remove from registry
            success = self.server_registry.remove_server(server_id)
            return success

        return False

    def get_client(self, server_id: str) -> Optional[MCPClient]:
        """
        Get a client for a specific server.

        Args:
            server_id: ID of the server

        Returns:
            MCPClient instance or None if not found
        """
        client_data = self.clients.get(server_id)
        if isinstance(client_data, dict) and 'client' in client_data:
            return client_data['client']
        return None

    async def list_known_servers(self):
        """
        Get a list of all known server IDs.

        Returns:
            List of server IDs
        """
        return self.server_registry.list_server_ids()

    async def list_known_servers_detailed(self):
        """
        Get detailed information about all known servers.

        Returns:
            List of MCPServerInfo objects
        """
        return self.server_registry.list_server_info()

    async def list_mcp_servers(self):
        """
        Get a list of all registered MCP servers with detailed information.

        Returns:
            Dictionary containing server information in a standardized format
        """
        server_details = await self.list_known_servers_detailed()

        servers_list = []
        for server in server_details:
            servers_list.append({
                "server_id": server.server_id,
                "server_url": server.server_url,
                "name": server.name,
                "description": server.description,
                "status": server.status,
                "last_connected": server.last_connected.isoformat() if server.last_connected else None,
                "capabilities": server.capabilities
            })

        return {
            "success": True,
            "servers": servers_list,
            "count": len(servers_list)
        }

    async def server_exists(self, server_id: str) -> bool:
        """
        Check if a server is known to the manager.

        Args:
            server_id: ID of the server to check

        Returns:
            True if the server exists in the registry, False otherwise
        """
        return self.server_registry.server_exists(server_id)

    async def remove_known_server(self, server_id: str) -> bool:
        """
        Remove an MCP server from the registry and disconnect if connected.

        Args:
            server_id: ID of the server to remove

        Returns:
            True if removal was successful, False otherwise
        """
        # Disconnect if currently connected
        if server_id in self.clients:
            await self.disconnect_from_server(server_id)
        else:
            # Just remove from registry if not connected
            return self.server_registry.remove_server(server_id)

        return True

    def register_notification_handler(self, notification_type: str, handler: Callable):
        """
        Register a handler for specific notification types from servers.

        Args:
            notification_type: Type of notification to handle
            handler: Function to call when notification is received
        """
        if notification_type not in self.notification_handlers:
            self.notification_handlers[notification_type] = []

        self.notification_handlers[notification_type].append(handler)

    # Methods for use by tool execution manager to get appropriate clients
    async def get_client_for_tool(self, tool_name: str) -> Optional[MCPClient]:
        """
        Get the appropriate client for a specific tool by checking known servers.

        Args:
            tool_name: Name of the tool to find

        Returns:
            MCPClient instance if a server with this tool is found, None otherwise
        """
        # Check all connected servers to see if any of them supports this tool
        for server_id, client_data in self.clients.items():
            if isinstance(client_data, dict) and 'client' in client_data:
                try:
                    client = client_data['client']
                    tools_response = await client.list_tools()
                    if tools_response and "tools" in tools_response:
                        tool_names = [tool.get("name", "") if isinstance(tool, dict) else str(tool) for tool in tools_response["tools"]]
                        if tool_name in tool_names:
                            return client
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error checking tools on server {server_id}: {e}")

        return None  # No client found with this tool

    async def _notify_tool_discovered_event(self, event_type: str, server_id: str, capabilities: List[str], server_url: str):
        """
        Notify that tools have been discovered from an MCP server.
        
        Args:
            event_type: Type of event (e.g., "tools_discovered")
            server_id: ID of the server
            capabilities: List of tool names discovered
            server_url: URL of the server
        """
        # If the tool discovery service is available, notify it
        if self._tool_discovery_service:
            if event_type == "tools_discovered":
                if self.logger:
                    self.logger.info(f"Notifying tool discovery service of server {server_id} with capabilities: {capabilities}")
                await self._tool_discovery_service.handle_tools_discovered(server_id, capabilities, server_url)
        else:
            if self.logger:
                self.logger.warning(f"Tool discovery service not available when handling event: {event_type} for server {server_id}")
        
        # Also call any registered notification handlers
        if event_type in self.notification_handlers:
            for handler in self.notification_handlers[event_type]:
                try:
                    await handler(server_id, capabilities, server_url)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in notification handler: {e}")