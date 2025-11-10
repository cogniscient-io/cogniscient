"""
MCP Client using the official Model Context Protocol SDK.

This module implements the MCP client using the official mcp package SDK.
The implementation now focuses on using existing sessions to perform MCP operations,
separating concerns from connection management to the client manager.
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from mcp.client.session import ClientSession


class MCPClient:
    """
    Application-level MCP client using the official mcp SDK.
    This class focuses on using an existing session to perform MCP operations.
    """

    def __init__(self, session: ClientSession, server_url: str):
        """
        Initialize the MCP client with an existing session.

        Args:
            session: The ClientSession instance to use for MCP operations
            server_url: URL of the server for identification
        """
        self.session = session
        self.server_url = server_url
        self.initialized = True  # Already initialized when session is passed
        self.logger = None  # Will be set by kernel

    async def list_tools(self) -> Optional[Dict[str, Any]]:
        """
        List tools available on the server using the official SDK.

        Returns:
            Dictionary containing the list of available tools or None if request failed
        """
        try:
            result = await self.session.list_tools()
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif isinstance(result, (dict, list)):
                return result
            elif hasattr(result, '__dict__'):
                # If it's an object, try to convert to dict
                return result.__dict__
            else:
                # If it's a response object, convert it to dict
                return {"result": str(result)}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to list tools: {e}")
            return {"tools": []}



    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call a specific tool on the server using the official SDK.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool execution

        Returns:
            Tool execution result or None if request failed
        """
        try:
            result = await self.session.call_tool(name=tool_name, arguments=params)
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif isinstance(result, (dict, list)):
                return result
            elif hasattr(result, '__dict__'):
                # If it's an object, try to convert to dict
                return result.__dict__
            else:
                # If it's a response object, convert it to dict
                return {"result": str(result)}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to call tool {tool_name}: {e}")
            return {"error": str(e)}

    async def list_prompts(self) -> Optional[Dict[str, Any]]:
        """
        List available prompts from the MCP server.
        
        Returns:
            List of available prompts or None if request failed
        """
        try:
            result = await self.session.list_prompts()
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif isinstance(result, (dict, list)):
                return result
            elif hasattr(result, '__dict__'):
                # If it's an object, try to convert to dict
                return result.__dict__
            else:
                # If it's a response object, convert it to dict
                return {"result": str(result)}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to list prompts: {e}")
            return None

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = {}) -> Optional[Dict[str, Any]]:
        """
        Get a specific prompt from the MCP server.

        Args:
            prompt_name: Name of the prompt to retrieve
            arguments: Arguments to pass to the prompt
            
        Returns:
            Prompt content or None if request failed
        """
        try:
            result = await self.session.get_prompt(name=prompt_name, arguments=arguments)
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif isinstance(result, (dict, list)):
                return result
            elif hasattr(result, '__dict__'):
                # If it's an object, try to convert to dict
                return result.__dict__
            else:
                # If it's a response object, convert it to dict
                return {"result": str(result)}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get prompt {prompt_name}: {e}")
            return None

    # Legacy methods to maintain backward compatibility with existing code
    # These map to the new methods
    async def submit_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Submit a tool execution to the server using the official SDK.
        (Backward compatibility method - uses call_tool)

        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool execution

        Returns:
            Execution ID of the submitted execution
        """
        result = await self.call_tool(tool_name, params)
        if result and 'result' in result:
            import uuid
            execution_id = str(uuid.uuid4())
            return execution_id
        else:
            raise Exception(f"Tool execution failed: {result}")

    async def get_execution_result(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the result of a tool execution from the server.
        Note: In MCP protocol, results are often streamed back rather than polled.
        (Backward compatibility method)

        Args:
            execution_id: ID of the execution to get result for

        Returns:
            Tool execution result or None if not found
        """
        if self.logger:
            self.logger.warning("Direct execution result polling not supported in MCP protocol")
        return None

