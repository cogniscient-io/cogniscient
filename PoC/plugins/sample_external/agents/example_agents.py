"""
Example agents demonstrating how to use the BaseExternalAgent class.

This module provides examples of implementing custom external agents.
"""

import time
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
import logging


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
    
    def register_tool(self, name: str, description: str = "", input_schema: dict = None):
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
    
    def run(self, transport: str = "stdio"):
        """
        Run the MCP external agent server synchronously.
        
        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
        """
        self.logger.info(f"Starting MCP external agent {self.name} with {transport} transport")
        self.mcp.run(transport=transport)
    
    async def run_async(self):
        """
        Run the MCP external agent server asynchronously.
        """
        self.logger.info(f"Starting MCP external agent {self.name}")
        # Since mcp.run() is blocking, we should run it differently for async
        # For now, we'll run it in a thread or use a different approach
        # This is a simplified version - in practice, you would handle async differently
        await self.mcp.run()
    
    def run_http_server(self, host: str = "127.0.0.1", port: int = 8080):
        """
        Run the MCP external agent as an HTTP server using streamable HTTP transport.
        
        Args:
            host: Host address for the HTTP server (default: 127.0.0.1)
            port: Port for the HTTP server (default: 8080)
        """
        self.logger.info(f"Starting MCP external agent HTTP server {self.name} on {host}:{port}")
        # Update the MCP server settings for HTTP
        self.mcp.settings.host = host
        self.mcp.settings.port = port
        self.mcp.run(transport="streamable-http")
    
    def run_sse_server(self, host: str = "127.0.0.1", port: int = 8080, mount_path: str = "/"):
        """
        Run the MCP external agent using Server-Sent Events (SSE) transport.
        
        Args:
            host: Host address for the SSE server (default: 127.0.0.1)
            port: Port for the SSE server (default: 8080)
            mount_path: Mount path for the SSE endpoints (default: "/")
        """
        self.logger.info(f"Starting MCP external agent SSE server {self.name} on {host}:{port}")
        # Update the MCP server settings for SSE
        self.mcp.settings.host = host
        self.mcp.settings.port = port
        self.mcp.run(transport="sse", mount_path=mount_path)

    def get_mcp_registration_info(self) -> dict:
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
            "supported_transports": ["stdio", "sse", "streamable-http"]
        }
        
        return registration_info


class ExampleMathAgent(BaseExternalAgent):
    """
    Example math agent that demonstrates the usage of BaseExternalAgent.
    """


class TimeAgent(BaseExternalAgent):
    """
    Example agent that provides time-related functionality.
    """
    
    def __init__(self):
        super().__init__(
            name="TimeAgent",
            version="1.0.0",
            description="An agent that provides time-related information"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "get_current_time", 
            description="Get the current time", 
            parameters={}
        )
        
        self.register_method(
            "sleep", 
            description="Pause execution for specified seconds", 
            parameters={
                "seconds": {"type": "number", "description": "Number of seconds to sleep", "required": True}
            }
        )
    
    def get_current_time(self) -> str:
        """Get the current time."""
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"Returning current time: {current_time}")
        return current_time
    
    def sleep(self, seconds: float) -> str:
        """Pause execution for specified seconds."""
        self.logger.info(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
        return f"Slept for {seconds} seconds"


class EchoAgent(BaseExternalAgent):
    """
    Example agent that echoes back the input with some processing.
    """
    
    def __init__(self):
        super().__init__(
            name="EchoAgent",
            version="1.0.0",
            description="An agent that echoes back provided text with processing"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "echo", 
            description="Echo back the input text", 
            parameters={
                "text": {"type": "string", "description": "Text to echo", "required": True}
            }
        )
        
        self.register_method(
            "count_chars", 
            description="Count characters in the input text", 
            parameters={
                "text": {"type": "string", "description": "Text to count characters for", "required": True}
            }
        )
    
    def echo(self, text: str) -> str:
        """Echo back the input text."""
        self.logger.info(f"Echoing: {text}")
        return f"ECHO: {text}"
    
    def count_chars(self, text: str) -> int:
        """Count characters in the input text."""
        count = len(text)
        self.logger.info(f"Character count for '{text[:20]}...': {count}")
        return count


class AsyncExampleAgent(BaseExternalAgent):
    """
    Example agent demonstrating async operations.
    """
    
    def __init__(self):
        super().__init__(
            name="AsyncExampleAgent",
            version="1.0.0",
            description="An agent that demonstrates async operations"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "fetch_data", 
            description="Simulate fetching data asynchronously", 
            parameters={
                "delay": {"type": "number", "description": "Delay in seconds", "required": False, "default": 1}
            }
        )
    
    async def fetch_data(self, delay: float = 1.0) -> dict:
        """Simulate fetching data asynchronously."""
        self.logger.info(f"Starting async fetch with {delay}s delay")
        await asyncio.sleep(delay)
        result = {
            "data": "some important data",
            "timestamp": time.time(),
            "delay_used": delay
        }
        self.logger.info(f"Completed async fetch: {result}")
        return result


if __name__ == "__main__":
    # Example: Run the TimeAgent
    agent = TimeAgent()
    agent.run(host="0.0.0.0", port=8002)