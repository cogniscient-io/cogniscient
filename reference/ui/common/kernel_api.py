"""
Kernel API client for UI components.
This provides a clean interface to the kernel that UI components can use.
"""

import asyncio
from typing import AsyncGenerator
from .base_ui import KernelAPIProtocol


class KernelAPIClient(KernelAPIProtocol):
    """API client that provides clean interface to the kernel for UI components."""
    
    def __init__(self, kernel):
        """
        Initialize the kernel API client.
        
        Args:
            kernel: The GCSKernel instance to communicate with
        """
        self.kernel = kernel
    
    async def send_user_prompt(self, prompt: str) -> str:
        """Send a user prompt and receive a complete response."""
        return await self.kernel.submit_prompt(prompt)
    
    async def stream_user_prompt(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream a user prompt and receive chunks."""
        async for chunk in self.kernel.stream_prompt(prompt):
            yield chunk
    
    def get_kernel_status(self) -> str:
        """Get kernel status."""
        return f"Kernel running: {self.kernel.is_running()}"
    
    async def get_available_tools(self):
        """Get all available tools from the kernel registry."""
        if self.kernel and self.kernel.registry:
            return self.kernel.registry.get_all_tools()
        return {}
    
    def list_registered_tools(self) -> list:
        """List registered tool names from the kernel registry."""
        if self.kernel and self.kernel.registry:
            tools = self.kernel.registry.get_all_tools()
            return list(tools.keys())
        return []
    
    async def execute_tool(self, tool_name: str, params: dict):
        """Execute a specific tool with parameters via dynamic dispatch to kernel."""
        # Get the tool definition from the registry
        if not self.kernel.registry:
            raise Exception("Kernel registry not available")
        
        tool = await self.kernel.registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        # Validate parameters against tool schema
        await self._validate_tool_parameters(tool, params)
        
        # Create a ToolDefinition from the registered tool
        from gcs_kernel.models import ToolDefinition
        tool_def = ToolDefinition.create(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters,
            display_name=tool.display_name,
            approval_required=getattr(tool, 'approval_required', True),
            approval_mode=getattr(tool, 'approval_mode', None)
        )
        
        # Submit to scheduler via kernel
        if not self.kernel.scheduler:
            raise Exception("Kernel scheduler not available")
        
        execution_id = await self.kernel.scheduler.submit_tool_execution(tool_def, params)
        return execution_id
    
    async def get_tool_result(self, execution_id: str):
        """Get the result of a tool execution via dynamic dispatch to kernel."""
        if not self.kernel.scheduler:
            raise Exception("Kernel scheduler not available")
        
        return self.kernel.scheduler.get_execution_result(execution_id)
    
    async def _validate_tool_parameters(self, tool, params: dict):
        """Validate parameters against the tool's parameter schema."""
        schema = getattr(tool, 'parameters', {})
        required_params = schema.get('required', [])
        
        # Check if all required parameters are present
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter '{param}' for tool '{tool.name}'")
        
        # Validate parameter types if schema defines them
        properties = schema.get('properties', {})
        for param_name, param_value in params.items():
            if param_name in properties:
                expected_type = properties[param_name].get('type')
                if expected_type == 'string' and not isinstance(param_value, str):
                    raise ValueError(f"Parameter '{param_name}' should be a string")
                elif expected_type == 'integer' and not isinstance(param_value, int):
                    raise ValueError(f"Parameter '{param_name}' should be an integer")
                elif expected_type == 'number' and not isinstance(param_value, (int, float)):
                    raise ValueError(f"Parameter '{param_name}' should be a number")
                elif expected_type == 'boolean' and not isinstance(param_value, bool):
                    raise ValueError(f"Parameter '{param_name}' should be a boolean")