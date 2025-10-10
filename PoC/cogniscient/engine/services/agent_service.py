"""Agent Service implementation following the ringed architecture."""

from typing import Any
from cogniscient.engine.services.service_interface import AgentServiceInterface
from cogniscient.engine.agent_utils.unified_agent_manager import UnifiedAgentManager


class AgentServiceImpl(AgentServiceInterface):
    """Implementation of AgentService following the ringed architecture."""
    
    def __init__(self, agents_dir: str = "custom/agents", runtime_ref=None):
        """Initialize the agent service.
        
        Args:
            agents_dir: Directory where agent modules are located
            runtime_ref: Reference to the runtime
        """
        self.unified_agent_manager = UnifiedAgentManager(
            agents_dir=agents_dir,
            runtime_ref=runtime_ref
        )
        
    async def initialize(self) -> bool:
        """Initialize the agent service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Agent service is initialized when unified agent manager is created
        return True
        
    async def shutdown(self) -> bool:
        """Shutdown the agent service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Clear all agents
        self.unified_agent_manager.agents.clear()
        return True

    async def load_agent(self, agent_name: str) -> Any:
        """Load an agent by name.
        
        Args:
            agent_name: Name of the agent to load
            
        Returns:
            Agent instance if successful, None otherwise
        """
        try:
            self.unified_agent_manager.load_agent(agent_name)
            return self.unified_agent_manager.get_agent(agent_name)
        except Exception as e:
            print(f"Failed to load agent {agent_name}: {e}")
            return None

    async def unload_agent(self, agent_name: str) -> bool:
        """Unload an agent by name.
        
        Args:
            agent_name: Name of the agent to unload
            
        Returns:
            True if unloading was successful, False otherwise
        """
        return self.unified_agent_manager.unload_agent(agent_name)

    async def run_agent_method(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Execute a method on an agent.
        
        Args:
            agent_name: Name of the agent
            method_name: Name of the method to execute
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
            
        Returns:
            Result of the method execution
        """
        return self.unified_agent_manager.run_agent(agent_name, method_name, *args, **kwargs)

    def set_runtime(self, runtime):
        """Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime
        if hasattr(self.unified_agent_manager, 'set_runtime') and self.unified_agent_manager:
            self.unified_agent_manager.set_runtime(runtime)

    async def load_all_agents(self, config: dict = None) -> bool:
        """
        Load all agents from the agents directory.
        
        Args:
            config: Configuration for the agents (optional)
            
        Returns:
            True if loading was successful, False otherwise
        """
        return self.unified_agent_manager.load_all_agents(config)

    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method for the agent service.
        """
        if not hasattr(self, 'gcs_runtime') or not self.gcs_runtime or not hasattr(self.gcs_runtime, 'mcp_service') or not self.gcs_runtime.mcp_service:
            print(f"Warning: No runtime reference for {self.__class__.__name__}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.gcs_runtime.mcp_service.mcp_client

        # Register load agent tool
        load_agent_tool = {
            "name": "agent_load_agent",
            "description": "Load an agent by name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent to load"}
                },
                "required": ["agent_name"]
            },
            "type": "function"
        }

        # Register load all agents tool
        load_all_agents_tool = {
            "name": "agent_load_all_agents",
            "description": "Load all available agents",
            "input_schema": {
                "type": "object",
                "properties": {
                    "config": {"type": "object", "description": "Configuration to apply to all agents (optional)"}
                }
            },
            "type": "function"
        }

        # Register unload agent tool
        unload_agent_tool = {
            "name": "agent_unload_agent",
            "description": "Unload an agent by name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent to unload"}
                },
                "required": ["agent_name"]
            },
            "type": "function"
        }

        # Register run agent method tool
        run_agent_method_tool = {
            "name": "agent_run_agent_method",
            "description": "Execute a method on an agent",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent"},
                    "method_name": {"type": "string", "description": "Name of the method to execute"},
                    "args": {"type": "array", "description": "Positional arguments to pass to the method", "default": []},
                    "kwargs": {"type": "object", "description": "Keyword arguments to pass to the method", "default": {}}
                },
                "required": ["agent_name", "method_name"]
            },
            "type": "function"
        }

        # Add tools to the registry
        agent_tools = mcp_client.tool_registry.get(self.__class__.__name__, [])
        agent_tools.extend([
            load_agent_tool,
            load_all_agents_tool,
            unload_agent_tool,
            run_agent_method_tool
        ])
        mcp_client.tool_registry[self.__class__.__name__] = agent_tools

        # Also register individual tool types
        for tool_desc in [
            load_agent_tool,
            load_all_agents_tool,
            unload_agent_tool,
            run_agent_method_tool
        ]:
            mcp_client.tool_types[tool_desc["name"]] = True  # Is a system tool