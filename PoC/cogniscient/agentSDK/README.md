# Agent SDK

This directory contains the infrastructure for creating and managing local agents in the Cognitive System framework.

## Table of Contents
1. [Overview](#overview)
2. [Creating a New Agent](#creating-a-new-agent)
3. [Agent Configuration](#agent-configuration)
4. [Agent Interface](#agent-interface)
5. [Dynamic Configuration](#dynamic-configuration)
6. [Examples](#examples)
7. [Best Practices](#best-practices)

## Overview

The Agent SDK provides a framework for developing two types of agents:

1. **Local agents** that run within the UCS system
2. **External agents** that run as separate HTTP services

Local agents inherit from the base `Agent` class and implement specific methods to perform tasks, while external agents are separate services that can be dynamically registered with the system.

The Agent base class is defined in `base.py` and requires implementations of the `self_describe()` method.

## Creating a New Local Agent

To create a new local agent, follow these steps:

1. Create a new Python file in the agents directory (default: `cogniscient/agentSDK`)
2. Define a class that inherits from `Agent`
3. Implement the required methods
4. Register the agent in configuration files if needed

Example:

```python
from cogniscient.agentSDK.base_local_agent import Agent

class MyNewLocalAgent(Agent):
    """A sample local agent that performs specific tasks."""
    
    def __init__(self, config=None):
        """Initialize the agent with configuration."""
        super().__init__()
        self.name = "MyNewLocalAgent"
        self.description = "A sample local agent for demonstration"
        # Apply configuration if provided
        if config:
            for key, value in config.items():
                setattr(self, key, value)

    def self_describe(self):
        """Describe the agent's capabilities."""
        return {
            "name": self.name,
            "description": self.description,
            "methods": {
                "perform_task": {
                    "description": "Perform a specific task",
                    "parameters": {
                        "param1": {
                            "type": "str",
                            "description": "A sample parameter",
                            "required": True
                        }
                    }
                }
            },
            "settings": {
                "timeout": 30,
                "retries": 3
            }
        }

    def perform_task(self, param1):
        """Perform the main task of the agent."""
        # Implementation here
        return f"Task performed with param1: {param1}"
```

## Creating a New External Agent

External agents run as separate HTTP services and can be dynamically registered with the UCS system. To create a new external agent:

1. Create a new Python file for your external agent
2. Define a class that inherits from `BaseExternalAgent`
3. Implement your custom methods
4. Register the methods using the `register_method` function

Example:

```python
from cogniscient.agentSDK.base_external_agent import BaseExternalAgent

class MyNewExternalAgent(BaseExternalAgent):
    """A sample external agent that runs as a separate service."""
    
    def __init__(self):
        super().__init__(
            name="MyNewExternalAgent",
            version="1.0.0",
            description="A sample external agent for demonstration"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "perform_task", 
            description="Perform a specific task", 
            parameters={
                "param1": {"type": "string", "description": "A sample parameter", "required": True}
            }
        )
    
    def perform_task(self, param1: str) -> str:
        """Perform the main task of the external agent."""
        # Implementation here
        return f"External task performed with param1: {param1}"

# To run the external agent server:
# agent = MyNewExternalAgent()
# agent.run()
```

## Agent Configuration

Agents can be configured through JSON files in the `configs` directory or via the system parameters service at runtime. The configuration schema includes:

- `name`: The unique identifier for the agent
- `version`: Version of the agent
- `enabled`: Whether the agent is enabled
- `parameter_ranges`: Parameter limits for the agent
- `approval_thresholds`: Thresholds for agent approval
- `orchestration_metadata`: Domain knowledge and safety constraints
- `settings`: Runtime settings like timeout and retries

## Agent Interface

There are two main types of agents with different interfaces:

### Local Agents
Local agents must implement the following interface:

- `self_describe()`: Return a description of the agent's capabilities
- Any custom methods the agent provides

The base `Agent` class is an abstract class that provides the common interface for local agents.

### External Agents
External agents use the `BaseExternalAgent` base class and provide:

- A FastAPI web server interface
- Dynamic method registration through HTTP endpoints
- Automatic endpoint generation for registered methods

## Dynamic Configuration

Agents and their locations can be dynamically modified at runtime through the system parameters service:

```python
# Update agents directory
result = ucs.system_parameters_service.set_system_parameter('agents_dir', '/path/to/new/agents')

# Update configuration directory
result = ucs.system_parameters_service.set_system_parameter('config_dir', '/path/to/new/configs')

# Update LLM settings
result = ucs.system_parameters_service.set_system_parameter('llm_model', 'new_model')
result = ucs.system_parameters_service.set_system_parameter('llm_base_url', 'http://newurl:port')
```

## Examples

See sample local agents in the `plugins/sample/agents/` directory and external agents in the `plugins/sample/agents/example_agents.py` for examples of how to implement agents within this framework.

## Best Practices

### For Local Agents:
1. **Inheritance**: Always inherit from the base `Agent` class
2. **Self-Description**: Implement `self_describe()` to clearly explain the agent's capabilities
3. **Error Handling**: Implement proper error handling in your agent methods
4. **Configuration**: Use the configuration system to make agents configurable
5. **Parameter Validation**: Always validate inputs to agent methods
6. **Consistent Naming**: Use PascalCase for agent class names to match the file naming convention

### For External Agents:
7. **Inheritance**: Always inherit from the `BaseExternalAgent` class  
8. **Method Registration**: Use `register_method()` to properly register your methods with metadata
9. **HTTP Endpoints**: Your methods will be automatically exposed as HTTP endpoints

### General:
10. **Documentation**: Document your agent's methods and parameters clearly
11. **Testing**: Create unit tests for your agents
12. **Security**: Validate all inputs to prevent injection attacks
13. **Logging**: Use proper logging to track agent execution