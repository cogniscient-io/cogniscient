"""Generic Control System (GCS) Runtime for PoC.
For backward compatibility, this is still named ucs_runtime.py and exports UCSRuntime.
"""

import importlib.util
import json
import os
from typing import Any, Dict, List
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.services.contextual_llm_service import ContextualLLMService
import datetime
from cogniscient.engine.agent_utils.local_agent_manager import LocalAgentManager
from cogniscient.engine.agent_utils.external_agent_manager import ExternalAgentManager
from cogniscient.engine.agent_utils.unified_agent_manager import UnifiedAgentManager, ComponentType, UnifiedComponent
from cogniscient.engine.agent_utils.agent_coordinator import AgentCoordinator
from cogniscient.engine.services.config_service import ConfigService
from cogniscient.engine.services.system_parameters_service import SystemParametersService


class GCSRuntime:
    """Core GCS runtime for loading and managing agents."""

    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK"):
        """Initialize the GCS runtime.
        
        Args:
            config_dir (str): Directory to load agent configurations from.
            agents_dir (str): Directory where agent modules are located.
        """
        # Validate config_dir and set to default if invalid
        if config_dir and not os.path.exists(config_dir):
            print(f"Warning: Config directory '{config_dir}' does not exist. Using default: '.'")
            self.config_dir = "."
        else:
            self.config_dir = config_dir or "."
        
        # Validate agents_dir and set to default if invalid
        if agents_dir and not os.path.exists(agents_dir):
            print(f"Warning: Agents directory '{agents_dir}' does not exist. Using default: 'cogniscient/agentSDK'")
            self.agents_dir = "cogniscient/agentSDK"
        else:
            self.agents_dir = agents_dir or "cogniscient/agentSDK"
        self.additional_prompt_info: Dict[str, Any] = {}
        # Track last call information for each agent
        self.agent_last_call: Dict[str, Dict[str, Any]] = {}
        # Create the contextual LLM service without agent registry initially
        self.llm_service = ContextualLLMService(LLMService())
        # Agent registry will be set after agents are loaded
        # Set a reference to self in the runtime for agents to access
        self.runtime_ref = self
        # Keep track of chat interfaces that need to be notified of configuration changes
        self.chat_interfaces: List[Any] = []

        # Initialize core system services that should always be available
        self.config_service = ConfigService()
        self.config_service.update_config_dir(config_dir)
        self.system_parameters_service = SystemParametersService()

        # Set runtime references in the services
        self.config_service.set_runtime(self)
        self.system_parameters_service.set_runtime(self)

        # Initialize the unified agent manager that handles both agents and services
        self.unified_agent_manager = UnifiedAgentManager(
            config_dir=config_dir,
            agents_dir=agents_dir,
            system_parameters_service=self.system_parameters_service
        )
        
        # Register the internal services with the unified manager
        config_service_component = UnifiedComponent(
            name="ConfigManager",
            component_type=ComponentType.INTERNAL_SERVICE,
            config={"service_type": "config"},
            load_behavior="static"
        )
        system_params_service_component = UnifiedComponent(
            name="SystemParametersManager",
            component_type=ComponentType.INTERNAL_SERVICE,
            config={"service_type": "system_parameters"},
            load_behavior="static"
        )
        
        self.unified_agent_manager.register_component(config_service_component)
        self.unified_agent_manager.register_component(system_params_service_component)

        # Initialize legacy agent management utilities for backward compatibility
        self.local_agent_manager = LocalAgentManager(
            config_dir=config_dir,
            agents_dir=agents_dir,
            system_parameters_service=self.system_parameters_service
        )
        self.external_agent_manager = ExternalAgentManager()
        self.agent_coordinator = AgentCoordinator(self.local_agent_manager, self.external_agent_manager)

        # Store references for backward compatibility but delegate functionality to unified_agent_manager
        self.agent_configs = self.local_agent_manager.agent_configs

        # Set the runtime reference for agents that need access to runtime functionality
        self.local_agent_manager.set_runtime_ref(self)
        self.unified_agent_manager.set_runtime_ref(self)

    @property
    def agents(self):
        """Property to access agents through the unified manager for backward compatibility."""
        all_agents = self.unified_agent_manager.get_all_agents()
        # Filter out system services to maintain backward compatibility
        filtered_agents = {name: agent for name, agent in all_agents.items() 
                          if name not in ["ConfigManager", "SystemParametersManager"]}
        return filtered_agents

    def load_agent_config(self, config_file: str) -> Dict[str, Any]:
        """Load an agent configuration from a JSON file.
        
        Args:
            config_file (str): Path to the configuration file.
            
        Returns:
            dict: The loaded configuration.
        """
        with open(config_file, "r") as f:
            return json.load(f)

    def load_agent_from_config(self, config: Dict[str, Any]) -> Any:
        """Load an agent module based on its configuration.
        
        Args:
            config (dict): The agent configuration.
            
        Returns:
            module: The loaded agent module.
        """
        if not config.get("enabled", True):
            return None
            
        name = config["name"]
        # Try to get the module path from the configuration first, then fall back to convention
        # This makes the system more flexible for different agent locations
        module_path = config.get("module_path")
        
        if module_path is None:
            # For this PoC, we'll assume a simple mapping from name to file path
            # In a more complex system, this would be part of the configuration
            if name == "SampleAgentA":
                module_path = os.path.join(self.agents_dir, "sample_agent_a.py")
            elif name == "SampleAgentB":
                module_path = os.path.join(self.agents_dir, "sample_agent_b.py")
            # ConfigManager and SystemParametersManager are now services, not loaded as agents
            # These are handled via service calls in run_agent method
            else:
                # Default path for other agents
                module_path = os.path.join(self.agents_dir, f"{name.lower()}.py")
        
        # Ensure the module path exists
        if not os.path.exists(module_path):
            raise FileNotFoundError(f"Agent module not found at {module_path}")
        
        spec = importlib.util.spec_from_file_location(name, module_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {name}")
        
        module = importlib.util.module_from_spec(spec)
        if spec.loader is not None:
            spec.loader.exec_module(module)
        return module

    def initialize_agent(self, config: Dict[str, Any]) -> Any:
        """Initialize an agent instance from its loaded module.
        
        Args:
            config (dict): The agent configuration.
            
        Returns:
            Agent: An initialized agent instance.
        """
        module = self.load_agent_from_config(config)
        if module is None:
            return None
            
        # For this PoC, we'll assume the agent class name matches the module name
        # This is a simplification - a real system would be more flexible
        class_name = config["name"]
        agent_class = getattr(module, class_name)
        
        # Initialize the agent with the configuration
        agent_instance = agent_class(config)
        
        # If the agent has a method to set the runtime reference, use it
        if hasattr(agent_instance, "set_runtime"):
            agent_instance.set_runtime(self)
            
        return agent_instance

    def load_all_agents(self) -> None:
        """Load all agents based on configuration files."""
        # Use the configuration manager to load all agent configs and load them
        agent_configs = self.local_agent_manager.config_manager.load_all_agent_configs()
        # Exclude the ConfigManager and SystemParametersManager since they're now services
        agent_names = [name for name in agent_configs.keys() 
                      if name not in ["ConfigManager", "SystemParametersManager"]]
        
        # Use the unified agent manager to load agents
        for agent_name in agent_names:
            if agent_name in agent_configs:
                agent_config = agent_configs[agent_name]
                if agent_config.get("enabled", True):
                    # Create a local agent component and register it
                    from cogniscient.engine.agent_utils.base_agent_manager import ComponentType, UnifiedComponent
                    local_agent_component = UnifiedComponent(
                        name=agent_name,
                        component_type=ComponentType.LOCAL_AGENT,
                        config=agent_config,
                        load_behavior="dynamic"
                    )
                    self.unified_agent_manager.register_component(local_agent_component)
        
        # Ensure agents have access to the runtime reference
        self.local_agent_manager.set_runtime_ref(self)
        self.unified_agent_manager.set_runtime_ref(self)
        
        # Set the agent registry in the LLM service
        self.llm_service.set_agent_registry(self.agents)

    def load_configuration(self, config_name: str) -> None:
        """Load a specific configuration which determines which agents to load.
        
        Args:
            config_name (str): Name of the configuration to load (without .json extension).
        """
        # Use the ConfigService to load the configuration
        result = self.config_service.load_configuration(config_name)
        if result["status"] == "error":
            raise ValueError(result["message"])
            
        config = result["configuration"]
        print(f"Loading configuration: {config['name']}")
        
        # Store additional prompt info temporarily
        temp_additional_prompt_info = config.get("additional_prompt_info", {})
        
        # Unload all currently loaded agents
        self.unload_all_agents()
        
        # Restore additional prompt info after unloading
        self.additional_prompt_info = temp_additional_prompt_info
        
        # Load agents specified in the configuration, excluding system services
        agent_specs = [agent_spec for agent_spec in config.get("agents", []) 
                      if agent_spec["name"] not in ["ConfigManager", "SystemParametersManager"]]
        
        # Use the unified agent manager to load the specified agents
        for agent_spec in agent_specs:
            agent_name = agent_spec["name"]
            config_file = agent_spec.get("config_file", f"config_{agent_name}.json")
            
            # Check if config_file is a relative path or just a filename
            if not os.path.isabs(config_file):
                config_path = os.path.join(self.config_dir, config_file)
            else:
                config_path = config_file
            
            # Load the configuration from the specified file
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    agent_config = json.load(f)
            else:
                print(f"Configuration file not found: {config_path}")
                continue
            
            # Get the merged configuration (defaults from code + values from config file)
            merged_config = self.local_agent_manager.config_manager.get_merged_config(agent_name)
            # If merged config was created, use it, otherwise use the loaded config
            if merged_config is None:
                merged_config = agent_config
            
            if merged_config and merged_config.get("enabled", True):
                # Create a local agent component and register it with the unified manager
                from cogniscient.engine.agent_utils.base_agent_manager import ComponentType, UnifiedComponent
                local_agent_component = UnifiedComponent(
                    name=agent_name,
                    component_type=ComponentType.LOCAL_AGENT,
                    config=merged_config,
                    load_behavior="dynamic"
                )
                self.unified_agent_manager.register_component(local_agent_component)
        
        # Ensure agents have access to the runtime reference
        self.local_agent_manager.set_runtime_ref(self)
        self.unified_agent_manager.set_runtime_ref(self)
        
        # Set the agent registry in the LLM service
        self.llm_service.set_agent_registry(self.agents)
        
        # Notify chat interfaces that the configuration has changed
        self._notify_configuration_change()
    
    def _notify_configuration_change(self) -> None:
        """Notify chat interfaces that the configuration has changed."""
        for chat_interface in self.chat_interfaces:
            if hasattr(chat_interface, "clear_conversation_history"):
                chat_interface.clear_conversation_history()
        print("Conversation history cleared due to configuration change")

    def register_chat_interface(self, chat_interface) -> None:
        """Register a chat interface to be notified of configuration changes.
        
        Args:
            chat_interface: The chat interface to register.
        """
        if chat_interface not in self.chat_interfaces:
            self.chat_interfaces.append(chat_interface)

    def unregister_chat_interface(self, chat_interface) -> None:
        """Unregister a chat interface.
        
        Args:
            chat_interface: The chat interface to unregister.
        """
        if chat_interface in self.chat_interfaces:
            self.chat_interfaces.remove(chat_interface)

    def unload_all_agents(self) -> None:
        """Unload all currently loaded agents."""
        # Delegate to the local agent manager
        self.local_agent_manager.unload_all_agents()
        
        # Also unload and remove components managed by the unified agent manager
        component_names = list(self.unified_agent_manager.components.keys())
        for name in component_names:
            # Skip system services that should remain loaded
            if name not in ["ConfigManager", "SystemParametersManager"]:
                self.unified_agent_manager.unload_component(name)
                # Remove the component from the registry entirely
                del self.unified_agent_manager.components[name]
        
        # Clear additional tracking
        self.agent_last_call.clear()
        # Note: We don't clear additional_prompt_info here as it's set by load_configuration
        
        # Update the LLM service with empty agent registry
        self.llm_service.set_agent_registry(self.agents)

    def list_available_configurations(self) -> List[str]:
        """List all available configuration files.
        
        Returns:
            List[str]: List of available configuration names.
        """
        # Use the ConfigService to get available configurations
        result = self.config_service.list_configurations()
        if result["status"] == "success":
            return [config["name"] for config in result["configurations"]]
        else:
            return []

    def run_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Any:
        """Run a specific method on an agent.
        
        Args:
            agent_name (str): Name of the agent to run.
            method_name (str): Name of the method to execute.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution.
        """
        # Check if this is a request for the config service
        if agent_name == "ConfigManager":
            return self._handle_config_service_request(method_name, *args, **kwargs)
        
        # Check if this is a request for the system parameters service
        if agent_name == "SystemParametersManager":
            return self._handle_system_parameters_service_request(method_name, *args, **kwargs)
        
        # Record the call information
        call_time = datetime.datetime.now()
        call_info = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
            "timestamp": call_time.isoformat()
        }
        
        try:
            # Use the unified agent manager to run the agent method
            result = self.unified_agent_manager.run_component_method(agent_name, method_name, *args, **kwargs)
            call_info["result"] = result
        except ValueError as e:
            # Record the error and re-raise
            call_info["result"] = {"error": str(e)}
            raise
        except Exception as e:
            call_info["result"] = {"error": str(e)}
            raise
        finally:
            # Store the call information
            self.agent_last_call[agent_name] = call_info
            
        return result

    def _handle_config_service_request(self, method_name: str, *args, **kwargs) -> Any:
        """Handle requests that should be directed to the ConfigService.
        
        Args:
            method_name (str): Name of the method to execute on ConfigService.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution on ConfigService.
        """
        method = getattr(self.config_service, method_name)
        return method(*args, **kwargs)

    def _handle_system_parameters_service_request(self, method_name: str, *args, **kwargs) -> Any:
        """Handle requests that should be directed to the SystemParametersService.
        
        Args:
            method_name (str): Name of the method to execute on SystemParametersService.
            *args: Positional arguments to pass to the method.
            **kwargs: Keyword arguments to pass to the method.
            
        Returns:
            The result of the method execution on SystemParametersService.
        """
        method = getattr(self.system_parameters_service, method_name)
        return method(*args, **kwargs)

    def shutdown(self) -> None:
        """Shutdown all agents."""
        # Unload all components managed by the unified agent manager
        for name in list(self.unified_agent_manager.components.keys()):
            # Skip system services during shutdown since they're singleton instances
            if name not in ["ConfigManager", "SystemParametersManager"]:
                self.unified_agent_manager.unload_component(name)
        
        # Also delegate to the local agent manager's unload functionality
        self.local_agent_manager.unload_all_agents()


# For backward compatibility
UCSRuntime = GCSRuntime


async def main():
    gcs = GCSRuntime()
    gcs.load_all_agents()
    
    # Simple demonstration of running agents
    try:
        result_a = gcs.run_agent("SampleAgentA", "perform_dns_lookup")
        if "error" in result_a and result_a["error"]:
            try:
                llmContent = f"Agent SampleAgentA encountered an error: {result_a['error']}"
                llm_response = await gcs.llm_service.generate_response(llmContent, domain="IT Networking")
                print(f"SampleAgentA error: {result_a['error']}")
                print(f"LLM suggestion: {llm_response}")
            except Exception as llm_e:
                print(f"Failed to get LLM suggestion: {llm_e}")
        else:
            print(f"SampleAgentA result: {result_a}")
        
        result_b = gcs.run_agent("SampleAgentB", "perform_website_check")
        print(f"SampleAgentB result: {result_b}")
    finally:
        gcs.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())