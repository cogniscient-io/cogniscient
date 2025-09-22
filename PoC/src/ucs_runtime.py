"""Universal Control System (UCS) Runtime for PoC."""

import importlib.util
import json
from typing import Any, Dict
from src.services.llm_service import LLMService
from src.services.contextual_llm_service import ContextualLLMService
import datetime

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
        # Track last call information for each agent
        self.agent_last_call: Dict[str, Dict[str, Any]] = {}
        # Create the contextual LLM service without agent registry initially
        self.llm_service = ContextualLLMService(LLMService())
        # Agent registry will be set after agents are loaded

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
        return agent_class(config)

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
        
        # Set the agent registry in the LLM service
        self.llm_service.set_agent_registry(self.agents)

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
        # Record the call information
        call_time = datetime.datetime.now()
        call_info = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
            "timestamp": call_time.isoformat()
        }
        
        if agent_name not in self.agents:
            # Record the error and raise
            call_info["result"] = {"error": f"Agent {agent_name} not loaded"}
            self.agent_last_call[agent_name] = call_info
            raise ValueError(f"Agent {agent_name} not loaded")
            
        agent = self.agents[agent_name]
        if not hasattr(agent, method_name):
            # Record the error and raise
            call_info["result"] = {"error": f"Agent {agent_name} does not have method {method_name}"}
            self.agent_last_call[agent_name] = call_info
            raise ValueError(f"Agent {agent_name} does not have method {method_name}")
            
        try:
            method = getattr(agent, method_name)
            result = method(*args, **kwargs)
            call_info["result"] = result
        except Exception as e:
            call_info["result"] = {"error": str(e)}
            raise
        finally:
            # Store the call information
            self.agent_last_call[agent_name] = call_info
            
        return result

    def shutdown(self) -> None:
        """Shutdown all agents."""
        for agent_name, agent in self.agents.items():
            if hasattr(agent, "shutdown"):
                agent.shutdown()
        print("All agents shut down.")


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