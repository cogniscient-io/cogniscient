"""Universal Control System (UCS) Runtime for PoC."""

import importlib.util
import json
from typing import Any, Dict


class UCSRuntime:
    """Core UCS runtime for loading and managing agents."""

    def __init__(self, config_dir: str = "."):
        """Initialize the UCS runtime.
        
        Args:
            config_dir (str): Directory to load agent configurations from.
        """
        self.config_dir = config_dir
        self.agents: Dict[str, Any] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}

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
        if not config.get("enabled", False):
            return None
            
        name = config["name"]
        # For this PoC, we'll assume a simple mapping from name to file path
        # In a more complex system, this would be part of the configuration
        module_path = "src/agents/sample_agent_a.py" if name == "SampleAgentA" else "src/agents/sample_agent_b.py"
        
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
        return agent_class()

    def load_all_agents(self) -> None:
        """Load all agents based on configuration files."""
        # For this PoC, we'll explicitly load our two sample agents
        # A real system would scan the config directory
        config_files = ["config_SampleAgentA.json", "config_SampleAgentB.json"]
        
        for config_file in config_files:
            try:
                config = self.load_agent_config(config_file)
                self.agent_configs[config["name"]] = config
                agent = self.initialize_agent(config)
                if agent is not None:
                    self.agents[config["name"]] = agent
                    print(f"Loaded agent: {config['name']}")
            except Exception as e:
                print(f"Failed to load agent from {config_file}: {e}")

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
        if agent_name not in self.agents:
            raise ValueError(f"Agent {agent_name} not loaded")
            
        agent = self.agents[agent_name]
        if not hasattr(agent, method_name):
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
            
        method = getattr(agent, method_name)
        return method(*args, **kwargs)

    def shutdown(self) -> None:
        """Shutdown all agents."""
        for agent_name, agent in self.agents.items():
            if hasattr(agent, "shutdown"):
                agent.shutdown()
        print("All agents shut down.")


if __name__ == "__main__":
    ucs = UCSRuntime()
    ucs.load_all_agents()
    
    # Simple demonstration of running agents
    try:
        result_a = ucs.run_agent("SampleAgentA", "perform_dns_lookup")
        print(f"SampleAgentA result: {result_a}")
        
        result_b = ucs.run_agent("SampleAgentB", "perform_website_check")
        print(f"SampleAgentB result: {result_b}")
    finally:
        ucs.shutdown()