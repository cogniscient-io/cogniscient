"""
MCP (Model Context Protocol) Client implementation for the GCS Kernel.

This module implements the MCPClient class which connects to external
tool servers and communicates with the kernel MCP server.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from gcs_kernel.models import MCPConfig, ToolResult


class MCPClient:
    """
    MCP client for connecting to external tool servers.
    Validates external tool schemas and capabilities, ensures secure
    communication with external MCP services.
    """
    
    def __init__(self, config: MCPConfig = None):
        """
        Initialize the MCP client with configuration.
        
        Args:
            config: Optional MCP configuration
        """
        self.config = config or MCPConfig(server_url="http://localhost:8000")
        self.session = None
        self.logger = None  # Will be set by kernel
        self.initialized = False

    async def initialize(self):
        """Initialize the MCP client."""
        import httpx
        self.session = httpx.AsyncClient(timeout=self.config.request_timeout)
        self.initialized = True
        
        if self.logger:
            self.logger.info(f"MCP client initialized with server: {self.config.server_url}")

    async def shutdown(self):
        """Shutdown the MCP client."""
        if self.session:
            await self.session.aclose()
        self.initialized = False
        
        if self.logger:
            self.logger.info("MCP client shutdown")

    async def connect_to_server(self):
        """
        Connect to the MCP server and verify connectivity.
        
        Returns:
            Connection result object
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            response = await self.session.get(f"{self.config.server_url}/health")
            if response.status_code == 200:
                return {"success": True, "message": "Connected to server successfully"}
            else:
                return {"success": False, "message": f"Server returned status: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to connect: {str(e)}"}

    async def list_tools(self) -> Dict[str, Any]:
        """
        List tools available on the server.
        
        Returns:
            Dictionary containing the list of available tools
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            response = await self.session.get(f"{self.config.server_url}/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to list tools: {e}")
            return {"tools": []}

    async def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific tool.
        
        Args:
            tool_name: Name of the tool to get details for
            
        Returns:
            Tool details or None if not found
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            response = await self.session.get(f"{self.config.server_url}/tools/{tool_name}")
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get tool {tool_name}: {e}")
            return None

    async def submit_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Submit a tool execution to the server.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool execution
            
        Returns:
            Execution ID of the submitted execution
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            response = await self.session.post(
                f"{self.config.server_url}/tools/{tool_name}/execute",
                json=params
            )
            response.raise_for_status()
            result = response.json()
            return result.get("execution_id", "")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to submit tool execution: {e}")
            raise e

    async def get_execution_result(self, execution_id: str) -> Optional[ToolResult]:
        """
        Get the result of a tool execution.
        
        Args:
            execution_id: ID of the execution to get result for
            
        Returns:
            ToolResult object or None if not found
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            response = await self.session.get(f"{self.config.server_url}/executions/{execution_id}")
            if response.status_code == 200:
                execution_data = response.json()
                
                # Convert the response to a ToolResult
                result_data = execution_data.get("result")
                if result_data:
                    return ToolResult(
                        tool_name=execution_data["tool_name"],
                        llm_content=result_data.get("llm_content", ""),
                        return_display=result_data.get("return_display", ""),
                        success=result_data.get("success", True),
                        error=result_data.get("error")
                    )
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get execution result: {e}")
            return None

    async def list_executions(self) -> Dict[str, Any]:
        """
        List recent tool executions.
        
        Returns:
            Dictionary containing recent executions
        """
        # Note: This is a placeholder - the actual server may need a specific endpoint
        # for listing all executions
        if self.logger:
            self.logger.warning("List executions endpoint not implemented in server yet")
        return {"executions": []}

    async def validate_tool_schema(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """
        Validate tool parameters against the tool's schema.
        
        Args:
            tool_name: Name of the tool to validate against
            params: Parameters to validate
            
        Returns:
            True if validation passes, False otherwise
        """
        tool_info = await self.get_tool(tool_name)
        if not tool_info:
            return False
        
        schema = tool_info.get("parameters", {})
        if not schema:
            return True  # If no schema, assume valid
        
        # Basic validation based on schema definition
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required parameters
        for param in required:
            if param not in params:
                return False
        
        # Validate parameter types (simplified)
        for param_name, param_value in params.items():
            if param_name in properties:
                expected_type = properties[param_name].get("type")
                if expected_type == "string" and not isinstance(param_value, str):
                    return False
                elif expected_type == "integer" and not isinstance(param_value, int):
                    return False
                elif expected_type == "number" and not isinstance(param_value, (int, float)):
                    return False
                elif expected_type == "boolean" and not isinstance(param_value, bool):
                    return False
        
        return True