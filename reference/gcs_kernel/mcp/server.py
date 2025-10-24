"""
MCP (Model Context Protocol) Server implementation for the GCS Kernel.

This module implements the MCPServer class which exposes kernel functions
and tool execution capabilities via MCP interfaces.
"""

import asyncio
import json
from typing import Dict, Any, Callable, Optional
from fastapi import FastAPI, HTTPException
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
        
        # Register MCP endpoints
        self._register_endpoints()

    def _register_endpoints(self):
        """Register MCP-compliant endpoints."""
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "kernel_running": self.kernel.is_running() if self.kernel else False}
        
        @self.app.get("/tools")
        async def list_tools():
            """List all registered tools."""
            if self.kernel and self.kernel.registry:
                tools = self.kernel.registry.get_all_tools()
                return {
                    "tools": [
                        {
                            "name": name,
                            "description": getattr(tool, 'description', ''),
                            "parameter_schema": getattr(tool, 'parameter_schema', {})
                        }
                        for name, tool in tools.items()
                    ]
                }
            return {"tools": []}
        
        @self.app.get("/tools/{tool_name}")
        async def get_tool(tool_name: str):
            """Get details of a specific tool."""
            if self.kernel and self.kernel.registry:
                tool = await self.kernel.registry.get_tool(tool_name)
                if tool:
                    return {
                        "name": tool_name,
                        "description": getattr(tool, 'description', ''),
                        "parameter_schema": getattr(tool, 'parameter_schema', {})
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            else:
                raise HTTPException(status_code=500, detail="Registry not available")
        
        @self.app.post("/tools/{tool_name}/execute")
        async def execute_tool(tool_name: str, params: Dict[str, Any]):
            """Execute a tool with given parameters."""
            if self.kernel and self.kernel.scheduler:
                # Create a temporary ToolDefinition for validation
                # In a real system, this would come from the registry
                tool_def = ToolDefinition(
                    name=tool_name,
                    display_name=tool_name,
                    description=f"Tool {tool_name}",
                    parameter_schema={"type": "object", "properties": {}}
                )
                
                # Submit the tool execution
                execution_id = await self.kernel.scheduler.submit_tool_execution(tool_def, params)
                return {"execution_id": execution_id}
            else:
                raise HTTPException(status_code=500, detail="Scheduler not available")
        
        @self.app.get("/executions/{execution_id}")
        async def get_execution(execution_id: str):
            """Get status and result of an execution."""
            if self.kernel and self.kernel.scheduler:
                execution = self.kernel.scheduler.get_execution(execution_id)
                if execution:
                    return {
                        "id": execution.id,
                        "tool_name": execution.tool_name,
                        "state": execution.state.value,
                        "result": execution.result.dict() if execution.result else None,
                        "created_at": execution.created_at.isoformat(),
                        "executed_at": execution.executed_at.isoformat() if execution.executed_at else None,
                        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
                    }
                else:
                    raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
            else:
                raise HTTPException(status_code=500, detail="Scheduler not available")

        @self.app.get("/capabilities")
        async def get_capabilities():
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
            if self.kernel and hasattr(self.kernel, 'send_user_prompt'):
                prompt = request_data.get("prompt", "")
                response = await self.kernel.send_user_prompt(prompt)
                return {"response": response}
            else:
                raise HTTPException(status_code=500, detail="Kernel AI processing not available")

        @self.app.post("/ai/stream")
        async def stream_ai_request(request_data: Dict[str, Any]):
            """Stream an AI request through the kernel."""
            if self.kernel and hasattr(self.kernel, 'stream_user_prompt'):
                from fastapi.responses import StreamingResponse
                import json
                
                prompt = request_data.get("prompt", "")
                
                async def generate_stream():
                    async for chunk in self.kernel.stream_user_prompt(prompt):
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
            The execution ID
        """
        if self.kernel and self.kernel.scheduler:
            # Create a temporary ToolDefinition for validation
            tool_def = ToolDefinition(
                name=tool_name,
                display_name=tool_name,
                description=f"Tool {tool_name}",
                parameter_schema={"type": "object", "properties": {}}
            )
            
            # Submit the tool execution
            execution_id = await self.kernel.scheduler.submit_tool_execution(tool_def, params)
            return execution_id
        else:
            raise Exception("Kernel scheduler not available")
    
    async def get_execution_result(self, execution_id: str) -> Optional[ToolResult]:
        """
        Get the result of a tool execution.
        
        Args:
            execution_id: The ID of the execution to get the result for
            
        Returns:
            The ToolResult object or None if not found
        """
        if self.kernel and self.kernel.scheduler:
            return self.kernel.scheduler.get_execution_result(execution_id)
        else:
            raise Exception("Kernel scheduler not available")