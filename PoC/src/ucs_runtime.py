"""Universal Control System (UCS) Runtime for PoC."""

import importlib.util
import json
import os
from typing import Any, Dict, List
from src.services.llm_service import LLMService
from src.services.contextual_llm_service import ContextualLLMService
import datetime
from agent_utils.agent_config_manager import AgentConfigManager
from agent_utils.agent_loader import AgentLoader
from agent_utils.agent_coordinator import AgentCoordinator
from src.services.config_service import ConfigService
from src.services.system_parameters_service import SystemParametersService

class UCSRuntime:
    """Core UCS runtime for loading and managing agents."""

    def __init__(self, config_dir: str = ".", agents_dir: str = "src/agents"):
        """Initialize the UCS runtime.
        
        Args:
            config_dir (str): Directory to load agent configurations from.
            agents_dir (str): Directory where agent modules are located.
        """
        self.config_dir = config_dir
        self.agents_dir = agents_dir
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
        self.system_parameters_service = SystemParametersService()
        
        # Set runtime references in the services
        self.config_service.set_runtime(self)
        self.system_parameters_service.set_runtime(self)
        
        # Initialize agent management utilities for cleaner separation of concerns
        self.agent_loader = AgentLoader(config_dir=config_dir, agents_dir=agents_dir)
        self.agent_coordinator = AgentCoordinator(self.agent_loader)
        
        # Store references for backward compatibility but delegate functionality to agent_loader
        self.agents = self.agent_loader.agents
        self.agent_configs = self.agent_loader.agent_configs
        
        # Set the runtime reference for agents that need access to runtime functionality
        self.agent_loader.set_runtime_ref(self)

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
            elif name == "ConfigManager":
                module_path = os.path.join(self.agents_dir, "config_manager.py")
            elif name == "SystemParametersManager":
                module_path = os.path.join(self.agents_dir, "system_parameters_manager.py")
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
        agent_configs = self.agent_loader.config_manager.load_all_agent_configs()
        # Exclude the ConfigManager and SystemParametersManager since they're now services
        agent_names = [name for name in agent_configs.keys() 
                      if name not in ["ConfigManager", "SystemParametersManager"]]
        self.agent_loader.load_specific_agents_by_name(agent_names)
        
        # Ensure agents have access to the runtime reference
        self.agent_loader.set_runtime_ref(self)
        
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
        self.agent_loader.load_specific_agents(agent_specs)
        
        # Ensure agents have access to the runtime reference
        self.agent_loader.set_runtime_ref(self)
        
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
        # Delegate to the agent loader
        self.agent_loader.unload_all_agents()
        
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
            # Use the agent loader to run the agent method
            result = self.agent_loader.run_agent(agent_name, method_name, *args, **kwargs)
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
        # Delegate to the agent loader's unload functionality which handles shutdown
        self.agent_loader.unload_all_agents()


async def main():
    ucs = UCSRuntime()
    ucs.load_all_agents()
    
    # Simple demonstration of running agents
    try:
        result_a = ucs.run_agent("SampleAgentA", "perform_dns_lookup")
        if "error" in result_a and result_a["error"]:
            try:
                llmContent = f"Agent SampleAgentA encountered an error: {result_a['error']}"
                llm_response = await ucs.llm_service.generate_response(llmContent, domain="IT Networking")
                print(f"SampleAgentA error: {result_a['error']}")
                print(f"LLM suggestion: {llm_response}")
            except Exception as llm_e:
                print(f"Failed to get LLM suggestion: {llm_e}")
        else:
            print(f"SampleAgentA result: {result_a}")
        
        result_b = ucs.run_agent("SampleAgentB", "perform_website_check")
        print(f"SampleAgentB result: {result_b}")
    finally:
        ucs.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())