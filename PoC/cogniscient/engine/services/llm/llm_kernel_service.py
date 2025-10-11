"""LLM Service implementation following the ringed architecture."""

from cogniscient.engine.services.service_interface import LLMServiceInterface


class LLMKernelServiceImpl(LLMServiceInterface):
    """Implementation of LLMService following the ringed architecture."""
    
    def __init__(self, provider_manager=None, mcp_client_service=None):
        """Initialize the LLM service.
        
        Args:
            provider_manager: The LLM provider manager for handling LLM calls
            mcp_client_service: MCP client service for external agent connections
        """
        self.provider_manager = provider_manager
        self.mcp_client_service = mcp_client_service
        
    async def initialize(self) -> bool:
        """Initialize the LLM service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # For now, initialization is just confirming the service is ready
        # In a more complex implementation, we might initialize specific models or connections
        return True
        
    async def shutdown(self) -> bool:
        """Shutdown the LLM service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Close any resources held by the provider manager
        if self.provider_manager and hasattr(self.provider_manager, 'close'):
            try:
                await self.provider_manager.close()
                return True
            except Exception:
                pass
        return True

    async def generate_response(self, prompt: str, domain: str = "general") -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: The input prompt for the LLM
            domain: Domain context for the response
            
        Returns:
            Generated response from the LLM
        """
        if self.provider_manager:
            return await self.provider_manager.generate_response(prompt, domain=domain)
        else:
            return f"Mock response to: {prompt} [Domain: {domain}]"

    def set_provider(self, provider_name: str) -> None:
        """Set the LLM provider.
        
        Args:
            provider_name: Name of the provider to set
        """
        # This method assumes the underlying provider manager has a set_provider method
        if self.provider_manager and hasattr(self.provider_manager, 'set_provider'):
            self.provider_manager.set_provider(provider_name)
        else:
            # In the current implementation, the provider manager sets its provider during initialization
            # So for now we'll just note this limitation
            print(f"Provider {provider_name} setting not implemented in current provider manager")

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the LLM service.
        """
        if not hasattr(self, 'gcs_runtime') or not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register generate response tool
        generate_response_tool = {
            "name": "llm_generate_response",
            "description": "Generate a response from the LLM",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The input prompt for the LLM"},
                    "domain": {"type": "string", "description": "Domain context for the response", "default": "general"}
                },
                "required": ["prompt"]
            },
            "type": "function"
        }

        # Register set provider tool
        set_provider_tool = {
            "name": "llm_set_provider",
            "description": "Set the LLM provider",
            "input_schema": {
                "type": "object",
                "properties": {
                    "provider_name": {"type": "string", "description": "Name of the provider to set"}
                },
                "required": ["provider_name"]
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            generate_response_tool,
            set_provider_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            generate_response_tool,
            set_provider_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool