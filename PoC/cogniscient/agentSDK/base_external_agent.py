"""
MCP-based external agent implementation that can be used to create custom external agents.

This module provides a BaseExternalAgent class that can be inherited to create
custom external agents that implement the Model Context Protocol (MCP) as MCP servers.
These agents can be discovered and used by MCP clients like the Cogniscient system.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable, Awaitable
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pydantic import BaseModel


class BaseExternalAgent:
    """
    Base class for creating MCP-compliant external agents that act as MCP servers.
    
    This class provides the basic structure and utilities needed to create
    external agents that can be discovered and used by MCP clients like the
    Cogniscient Adaptive Control System.
    """
    
    def __init__(self, 
                 name: str, 
                 version: str = "1.0.0", 
                 description: str = "",
                 instructions: str = ""):
        """
        Initialize the base MCP external agent.
        
        Args:
            name: Name of the agent
            version: Version of the agent
            description: Description of the agent's functionality
            instructions: Instructions for how the agent should be used
        """
        self.name = name
        self.version = version
        self.description = description
        self.instructions = instructions
        
        # Create the MCP server instance
        self.mcp = FastMCP(
            name,
            instructions=instructions or description,
        )
        
        # Set up logging
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        
        # Add handlers to avoid "no handler" warnings
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def register_tool(self, name: str, description: str = "", input_schema: Optional[Dict] = None):
        """
        Register a tool with the agent that can be called by MCP clients.
        
        Args:
            name: Name of the tool (should be unique)
            description: Description of what the tool does
            input_schema: JSON schema describing the parameters the tool accepts
        """
        # Create a wrapper function that will call the actual method with context
        async def tool_wrapper(ctx: Context, **kwargs):
            try:
                # Call the specific method
                method = getattr(self, name, None)
                if method is None:
                    await ctx.error(f"Tool {name} not implemented")
                    raise AttributeError(f"Tool {name} not implemented")
                
                # Call the method with context
                result = await method(ctx, **kwargs)
                
                await ctx.info(f"Successfully executed tool {name}")
                return result
            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                await ctx.error(error_msg)
                raise
        
        # Register the tool with MCP
        self.mcp.tool(
            name=name,
            description=description,
        )(tool_wrapper)
    
    def run(self):
        """
        Run the MCP external agent server synchronously.
        """
        self.logger.info(f"Starting MCP external agent {self.name}")
        self.mcp.run()
    
    async def run_async(self):
        """
        Run the MCP external agent server asynchronously.
        """
        self.logger.info(f"Starting MCP external agent {self.name}")
        # Since mcp.run() is blocking, we should run it differently for async
        # For now, we'll run it in a thread or use a different approach
        # This is a simplified version - in practice, you would handle async differently
        await self.mcp.run()
    
    def get_mcp_registration_info(self) -> Dict[str, Any]:
        """
        Get the MCP registration information needed for tool discovery.
        
        Returns:
            Dictionary containing MCP registration information
        """
        registration_info = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "mcp_compliant": True,
            "mcp_exposed_methods": list(self.mcp._tool_manager._tools.keys()) if hasattr(self.mcp, '_tool_manager') else [],
        }
        
        return registration_info


class SimpleMathAgent(BaseExternalAgent):
    """
    Example implementation of a simple math agent to demonstrate MCP usage.
    """
    
    def __init__(self):
        super().__init__(
            name="SimpleMathAgent",
            version="1.0.0",
            description="A simple agent that performs basic math operations",
            instructions="Use this agent to perform basic mathematical operations like addition and multiplication."
        )
        
        # Register the tools this agent supports
        self.register_tool(
            "add", 
            description="Add two numbers", 
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        )
        
        self.register_tool(
            "multiply", 
            description="Multiply two numbers", 
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        )
    
    async def add(self, ctx: Context, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        await ctx.info(f"Calculated {a} + {b} = {result}")
        self.logger.info(f"Calculated {a} + {b} = {result}")
        return result
    
    async def multiply(self, ctx: Context, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        await ctx.info(f"Calculated {a} * {b} = {result}")
        self.logger.info(f"Calculated {a} * {b} = {result}")
        return result


if __name__ == "__main__":
    # Example usage
    agent = SimpleMathAgent()
    agent.run()


class SimpleMathAgent(BaseExternalAgent):
    """
    Example implementation of a simple math agent to demonstrate usage.
    """
    
    def __init__(self):
        super().__init__(
            name="SimpleMathAgent",
            version="1.0.0",
            description="A simple agent that performs basic math operations"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "add", 
            description="Add two numbers", 
            parameters={
                "a": {"type": "number", "description": "First number", "required": True},
                "b": {"type": "number", "description": "Second number", "required": True}
            }
        )
        
        self.register_method(
            "multiply", 
            description="Multiply two numbers", 
            parameters={
                "a": {"type": "number", "description": "First number", "required": True},
                "b": {"type": "number", "description": "Second number", "required": True}
            }
        )
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        result = a + b
        self.logger.info(f"Calculated {a} + {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        self.logger.info(f"Calculated {a} * {b} = {result}")
        return result


if __name__ == "__main__":
    # Example usage
    agent = SimpleMathAgent()
    agent.run()