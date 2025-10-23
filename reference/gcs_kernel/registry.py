"""
Tool Registry System implementation for the GCS Kernel.

This module implements the ToolRegistry class which manages available tools,
their registration, and discovery (command-based and MCP-based).
"""

import asyncio
from typing import Dict, Any, Optional, Protocol
from gcs_kernel.models import ToolDefinition, ToolResult


class BaseTool(Protocol):
    """
    Base interface for all tools in the GCS Kernel.
    
    All tools must implement this interface to be compatible with the kernel.
    """
    
    name: str
    display_name: str
    description: str
    parameter_schema: Dict[str, Any]
    
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters: The parameters for tool execution
            
        Returns:
            A ToolResult containing the execution result
        """
        ...


class ToolRegistry:
    """
    Tool Registry System that manages available tools, their registration,
    and discovery (command-based and MCP-based).
    """
    
    def __init__(self):
        """Initialize the tool registry with necessary components."""
        self.tools: Dict[str, BaseTool] = {}
        self.logger = None  # Will be set by kernel

    async def initialize(self):
        """Initialize the registry."""
        # Register built-in tools
        await self._register_built_in_tools()

    async def shutdown(self):
        """Shutdown the registry."""
        pass

    async def _register_built_in_tools(self):
        """Register built-in tools available to the kernel."""
        # In a real system, we would register actual built-in tools here
        pass

    async def register_tool(self, tool: BaseTool) -> bool:
        """
        Register a new tool with the registry.
        
        Args:
            tool: The tool to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Validate the tool
            if not hasattr(tool, 'name') or not hasattr(tool, 'execute'):
                if self.logger:
                    self.logger.error(f"Invalid tool: missing required attributes: {tool}")
                return False
            
            # Add the tool to the registry
            self.tools[tool.name] = tool
            
            if self.logger:
                self.logger.info(f"Tool registered: {tool.name}")
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to register tool: {e}")
            return False

    async def deregister_tool(self, tool_name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            tool_name: The name of the tool to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                
                if self.logger:
                    self.logger.info(f"Tool deregistered: {tool_name}")
                
                return True
            return False
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to deregister tool: {e}")
            return False

    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by its name from the registry.
        
        Args:
            tool_name: The name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(tool_name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            A dictionary of all registered tools
        """
        return self.tools.copy()

    async def discover_command_based_tools(self) -> Dict[str, BaseTool]:
        """
        Discover tools using command-based discovery mechanism.
        
        Returns:
            A dictionary of discovered tools
        """
        # In a real system, this would search for command-based tools
        # For now, return an empty dictionary
        return {}

    async def discover_mcp_based_tools(self) -> Dict[str, BaseTool]:
        """
        Discover tools using MCP-based discovery mechanism.
        
        Returns:
            A dictionary of discovered tools
        """
        # In a real system, this would connect to MCP servers and discover tools
        # For now, return an empty dictionary
        return {}