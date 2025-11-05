"""
MCP (Model Context Protocol) Server implementation for the GCS Kernel.

This module implements the MCPServer class which exposes kernel functions
and tool execution capabilities via MCP interfaces.
"""

import asyncio
import json
import secrets
from typing import Dict, Any, Callable, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import uvicorn
from gcs_kernel.models import MCPConfig, ToolDefinition, ToolExecution, ToolResult


class MCPServer:
    """
    MCP Server for kernel services using FastMCP reference implementation patterns.
    Exposes kernel functions and tool execution capabilities via MCP interfaces.
    """
    
    def __init__(self, config: MCPConfig):
        """
        Initialize the MCP server with configuration.
        
        Args:
            config: MCP configuration including server URL and authentication details
        """
        self.config = config
        self.app = FastAPI(title="GCS Kernel MCP Server")
        self.is_running = False
        self.server_process = None
        self.handlers: Dict[str, Callable] = {}
        self.kernel = None  # Will be set by kernel
        self.logger = None  # Will be set by kernel
        
        # Generate a secret token for basic authentication if not provided in config
        if not self.config.client_secret:
            self.config.client_secret = secrets.token_urlsafe(32)
        
        # Register MCP endpoints
        self._register_endpoints()

    async def _authenticate(self, authorization: str = Header(None)):
        """
        Authenticate incoming requests using the configured authentication method.
        
        Args:
            authorization: Authorization header from the request
            
        Raises:
            HTTPException: If authentication fails
        """
        if not self.config.client_secret:
            # If no authentication is configured, allow all requests
            return
        
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        if not secrets.compare_digest(token, self.config.client_secret):
            raise HTTPException(status_code=401, detail="Invalid authentication token")

    def _register_endpoints(self):
        """Register MCP-compliant endpoints."""
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "kernel_running": self.kernel.is_running() if self.kernel else False}
        
        @self.app.get("/tools")
        async def list_tools(auth=Depends(self._authenticate)):
            """List all registered tools."""
            if self.kernel and self.kernel.registry:
                tools = self.kernel.registry.get_all_tools()
                return {
                    "tools": [
                        {
                            "name": name,
                            "description": getattr(tool, 'description', ''),
                            "parameter_schema": getattr(tool, 'parameters', {})
                        }
                        for name, tool in tools.items()
                    ]
                }
            return {"tools": []}
        
        @self.app.get("/tools/{tool_name}")
        async def get_tool(tool_name: str, auth=Depends(self._authenticate)):
            """Get details of a specific tool."""
            if self.kernel and self.kernel.registry:
                tool = await self.kernel.registry.get_tool(tool_name)
                if tool:
                    return {
                        "name": tool_name,
                        "description": getattr(tool, 'description', ''),
                        "parameter_schema": getattr(tool, 'parameters', {})
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            else:
                raise HTTPException(status_code=500, detail="Registry not available")
        
        @self.app.post("/tools/{tool_name}/execute")
        async def execute_tool(tool_name: str, params: Dict[str, Any], auth=Depends(self._authenticate)):
            """Execute a tool with given parameters."""
            if self.kernel and hasattr(self.kernel, 'tool_execution_manager'):
                # Use the ToolExecutionManager to execute the tool on behalf of external client
                result = await self.kernel.tool_execution_manager.execute_tool_for_mcp_client(tool_name, params)
                
                # Return the result directly since ToolExecutionManager handles execution lifecycle
                return {
                    "tool_name": tool_name,
                    "result": result.dict(),
                    "success": result.success
                }
            else:
                raise HTTPException(status_code=500, detail="ToolExecutionManager not available")
        
        @self.app.post("/tools/{tool_name}/execute_stream")
        async def execute_tool_stream(tool_name: str, params: Dict[str, Any], auth=Depends(self._authenticate)):
            """Execute a tool with given parameters and stream the results."""
            from fastapi.responses import StreamingResponse
            import json
            
            if not (self.kernel and hasattr(self.kernel, 'tool_execution_manager')):
                raise HTTPException(status_code=500, detail="ToolExecutionManager not available")
            
            async def generate_stream():
                """Generate streaming updates for the tool execution."""
                # For now, return a simple execution result since the ToolExecutionManager
                # handles the execution lifecycle internally
                try:
                    # Directly execute the tool using the ToolExecutionManager
                    result = await self.kernel.tool_execution_manager.execute_tool_for_mcp_client(tool_name, params)
                    
                    # Yield the result when ready
                    status_update = {
                        "tool_name": tool_name,
                        "result": result.dict(),
                        "completed": True,
                        "success": result.success
                    }
                    yield f"data: {json.dumps(status_update)}\n\n"
                except Exception as e:
                    error_update = {
                        "tool_name": tool_name,
                        "error": str(e),
                        "completed": True,
                        "success": False
                    }
                    yield f"data: {json.dumps(error_update)}\n\n"
            
            return StreamingResponse(generate_stream(), media_type="text/plain")
        
        @self.app.get("/executions/{execution_id}")
        async def get_execution(execution_id: str, auth=Depends(self._authenticate)):
            """Get status and result of an execution."""
            # Note: With the new ToolExecutionManager architecture, execution status
            # is managed internally and tools are executed directly, returning results immediately.
            # In future, we might implement execution tracking in the ToolExecutionManager.
            # For now, return an appropriate message.
            raise HTTPException(status_code=404, detail="Execution tracking not available with ToolExecutionManager. Tools execute directly and return results.")

        @self.app.get("/capabilities")
        async def get_capabilities(auth=Depends(self._authenticate)):
            """Get the MCP capabilities of this server."""
            return {
                "version": "1.0",
                "capabilities": [
                    "tool-discovery",
                    "tool-execution",
                    "execution-monitoring",
                    "ai-interaction"
                ]
            }

        @self.app.post("/ai/process")
        async def process_ai_request(request_data: Dict[str, Any]):
            """Process an AI request through the kernel."""
            if self.kernel and hasattr(self.kernel, 'submit_prompt'):
                prompt = request_data.get("prompt", "")
                response = await self.kernel.submit_prompt(prompt)
                return {"response": response}
            else:
                raise HTTPException(status_code=500, detail="Kernel AI processing not available")

        @self.app.post("/ai/stream")
        async def stream_ai_request(request_data: Dict[str, Any]):
            """Stream an AI request through the kernel."""
            if self.kernel and hasattr(self.kernel, 'stream_prompt'):
                from fastapi.responses import StreamingResponse
                import json
                
                prompt = request_data.get("prompt", "")
                
                async def generate_stream():
                    async for chunk in self.kernel.stream_prompt(prompt):
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                
                return StreamingResponse(generate_stream(), media_type="text/plain")
            else:
                raise HTTPException(status_code=500, detail="Kernel AI streaming not available")

    async def start(self):
        """Start the MCP server."""
        if not self.is_running:
            self.is_running = True
            
            # Start the server in a separate process
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
            self.server_process = uvicorn.Server(config)
            
            # Run the server (this would normally be in a background task)
            # For now, we'll just prepare it to run
            print(f"MCP Server starting on {self.config.server_url}")
        
        if self.logger:
            self.logger.info(f"MCP Server started on {self.config.server_url}")

    async def stop(self):
        """Stop the MCP server."""
        if self.is_running and self.server_process:
            self.server_process.should_exit = True
            self.is_running = False
            
            if self.logger:
                self.logger.info("MCP Server stopped")

    def register_custom_handler(self, path: str, handler: Callable, method: str = "GET"):
        """Register a custom handler for a specific endpoint."""
        if method.upper() == "GET":
            @self.app.get(path)
            async def custom_get_handler():
                return await handler()
        elif method.upper() == "POST":
            @self.app.post(path)
            async def custom_post_handler(request_data: Dict[str, Any]):
                return await handler(request_data)

    async def submit_tool_execution(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Submit a tool execution via the MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool execution
            
        Returns:
            The execution ID (in the new architecture, this returns results directly)
        """
        if self.kernel and hasattr(self.kernel, 'tool_execution_manager'):
            # Use the ToolExecutionManager to execute the tool
            result = await self.kernel.tool_execution_manager.execute_tool_for_mcp_client(tool_name, params)
            # In the new architecture, tools execute directly and return results immediately
            # We return a pseudo-execution ID for compatibility
            import uuid
            execution_id = f"sync_{str(uuid.uuid4())}"
            # Store the result in a temporary location or return directly
            return execution_id
        else:
            raise Exception("ToolExecutionManager not available")
    
    async def get_execution_result(self, execution_id: str) -> Optional[ToolResult]:
        """
        Get the result of a tool execution.
        
        Args:
            execution_id: The ID of the execution to get the result for
            
        Returns:
            The ToolResult object or None if not found
        """
        # In the new architecture, this method is not directly supported
        # since tools execute and return results directly
        # This method might need to be deprecated or rethought
        return None