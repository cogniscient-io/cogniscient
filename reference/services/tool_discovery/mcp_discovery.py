"""
MCP Tool Discovery Service Implementation.

This module implements the ToolDiscoveryService which provides centralized
tool discovery and registration for external MCP servers.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from gcs_kernel.models import ToolResult
from gcs_kernel.registry import ToolRegistry


class ToolDiscoveryService:
    """
    Centralized service for handling MCP tool discovery and registration events.
    
    This service listens for events from connected MCP servers and manages
    the registration and deregistration of external tools in the kernel registry.
    """
    
    def __init__(self, kernel_registry: ToolRegistry):
        """
        Initialize the Tool Discovery Service.
        
        Args:
            kernel_registry: The kernel's tool registry to manage
        """
        self.registry = kernel_registry
        self.logger = None  # Will be set by kernel
        self._event_handlers: Dict[str, List[Callable]] = {
            "tools_discovered": [],
            "tool_added": [],
            "tool_removed": [],
            "tool_updated": []
        }
        
        # Track server-tool relationships for proper cleanup
        self._server_tool_map: Dict[str, List[str]] = {}
        
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event to handle
            handler: Function to call when event occurs
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        
        self._event_handlers[event_type].append(handler)
        
    async def handle_tools_discovered(self, server_id: str, capabilities: List[str], server_url: str):
        """
        Handle the event when tools are discovered from an MCP server.
        
        Args:
            server_id: ID of the server that has tools
            capabilities: List of tool names discovered on the server
            server_url: URL of the server for tool registration
        """
        if self.logger:
            self.logger.info(f"ToolDiscoveryService: Discovered {len(capabilities)} tools from server {server_id}: {capabilities}")
        
        # Store the relationship between server and its tools
        self._server_tool_map[server_id] = capabilities[:]
        
        # Register all tools as external tools
        for tool_name in capabilities:
            try:
                if self.logger:
                    self.logger.info(f"ToolDiscoveryService: Attempting to register external tool '{tool_name}' from server {server_id}")
                success = await self.registry.register_external_tool(tool_name, server_url)
                if success:
                    if self.logger:
                        self.logger.info(f"ToolDiscoveryService: Successfully registered external tool '{tool_name}' from server {server_id}")
                else:
                    if self.logger:
                        self.logger.warning(f"ToolDiscoveryService: Failed to register external tool '{tool_name}' from server {server_id}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"ToolDiscoveryService: Error registering external tool '{tool_name}' from server {server_id}: {e}")
        
        # Trigger event handlers
        await self._trigger_event_handlers("tools_discovered", server_id, capabilities, server_url)
        
    async def handle_tool_added(self, server_id: str, tool_name: str, server_url: str, tool_definition: Optional[Dict] = None):
        """
        Handle the event when a new tool is added to an MCP server.
        
        Args:
            server_id: ID of the server where tool was added
            tool_name: Name of the tool that was added
            server_url: URL of the server for tool registration
            tool_definition: Optional detailed definition of the tool
        """
        if self.logger:
            self.logger.info(f"Tool '{tool_name}' added to server {server_id}")
        
        # Add to the server's tool list
        if server_id not in self._server_tool_map:
            self._server_tool_map[server_id] = []
        if tool_name not in self._server_tool_map[server_id]:
            self._server_tool_map[server_id].append(tool_name)
        
        # Register as external tool
        try:
            success = await self.registry.register_external_tool(tool_name, server_url)
            if success:
                if self.logger:
                    self.logger.info(f"Successfully registered newly added tool '{tool_name}' from server {server_id}")
            else:
                if self.logger:
                    self.logger.warning(f"Failed to register newly added tool '{tool_name}' from server {server_id}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error registering newly added tool '{tool_name}' from server {server_id}: {e}")
        
        # Trigger event handlers
        await self._trigger_event_handlers("tool_added", server_id, tool_name, server_url, tool_definition)
        
    async def handle_tool_removed(self, server_id: str, tool_name: str):
        """
        Handle the event when a tool is removed from an MCP server.
        
        Args:
            server_id: ID of the server where tool was removed
            tool_name: Name of the tool that was removed
        """
        if self.logger:
            self.logger.info(f"Tool '{tool_name}' removed from server {server_id}")
        
        # Remove from the server's tool list
        if server_id in self._server_tool_map:
            if tool_name in self._server_tool_map[server_id]:
                self._server_tool_map[server_id].remove(tool_name)
        
        # Remove from registry
        try:
            success = await self.registry.deregister_external_tool(tool_name)
            if success:
                if self.logger:
                    self.logger.info(f"Successfully deregistered tool '{tool_name}' from server {server_id}")
            else:
                if self.logger:
                    self.logger.warning(f"Tool '{tool_name}' not found in registry for deregistration from server {server_id}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error deregistering tool '{tool_name}' from server {server_id}: {e}")
        
        # Trigger event handlers
        await self._trigger_event_handlers("tool_removed", server_id, tool_name)
        
    async def handle_tool_updated(self, server_id: str, tool_name: str, server_url: str, tool_definition: Dict):
        """
        Handle the event when a tool is updated on an MCP server.
        
        Args:
            server_id: ID of the server where tool was updated
            tool_name: Name of the tool that was updated
            server_url: URL of the server for tool registration
            tool_definition: Updated definition of the tool
        """
        if self.logger:
            self.logger.info(f"Tool '{tool_name}' updated on server {server_id}")
        
        # Update registration by re-registering
        try:
            # First deregister the old version
            await self.registry.deregister_external_tool(tool_name)
            
            # Then register the new version
            success = await self.registry.register_external_tool(tool_name, server_url)
            if success:
                if self.logger:
                    self.logger.info(f"Successfully updated tool '{tool_name}' from server {server_id}")
            else:
                if self.logger:
                    self.logger.warning(f"Failed to update tool '{tool_name}' from server {server_id}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating tool '{tool_name}' from server {server_id}: {e}")
        
        # Trigger event handlers
        await self._trigger_event_handlers("tool_updated", server_id, tool_name, server_url, tool_definition)
        
    async def handle_server_disconnect(self, server_id: str):
        """
        Handle the event when an MCP server disconnects.
        
        Args:
            server_id: ID of the server that disconnected
        """
        if self.logger:
            self.logger.info(f"Server {server_id} disconnected, cleaning up associated tools")
        
        # Remove all tools associated with this server
        if server_id in self._server_tool_map:
            tool_names = self._server_tool_map[server_id][:]
            
            for tool_name in tool_names:
                await self.handle_tool_removed(server_id, tool_name)
            
            # Clear the server's tool list
            del self._server_tool_map[server_id]
    
    async def _trigger_event_handlers(self, event_type: str, *args):
        """
        Trigger all handlers registered for a specific event type.
        
        Args:
            event_type: Type of event to trigger handlers for
            *args: Arguments to pass to handlers
        """
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in event handler for '{event_type}': {e}")
    
    def get_tools_for_server(self, server_id: str) -> List[str]:
        """
        Get all tools registered for a specific server.
        
        Args:
            server_id: ID of the server
            
        Returns:
            List of tool names registered for the server
        """
        return self._server_tool_map.get(server_id, [])
    
    def get_server_for_tool(self, tool_name: str) -> Optional[str]:
        """
        Get the server ID that hosts a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Server ID if found, None otherwise
        """
        for server_id, tool_list in self._server_tool_map.items():
            if tool_name in tool_list:
                return server_id
        return None