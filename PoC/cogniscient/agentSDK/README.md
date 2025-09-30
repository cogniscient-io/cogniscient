# Agent SDK

This directory contains the infrastructure for creating and managing local and external agents in the Cogniscient Adaptive Control System framework, with MCP (Model Context Protocol) integration.

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

1. **Local agents** that run within the Cogniscient system
2. **External agents** that run as MCP-compliant services using the Model Context Protocol

Local agents inherit from the base `Agent` class and implement specific methods to perform tasks, while external agents are MCP servers that can be discovered and used by the Cogniscient MCP client. The system uses MCP for standardized tool integration and orchestration.

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

External agents run as MCP-compliant services that can be discovered by the Cogniscient system as an MCP client. To create a new external agent:

1. Create a new Python file for your external agent
2. Define a class that inherits from `BaseExternalAgent`
3. Implement your custom async methods that accept `Context` as the first parameter
4. Register the tools using the `register_tool` function

Example:

```python
from mcp.server.fastmcp import Context
from cogniscient.agentSDK.base_external_agent import BaseExternalAgent

class MyNewExternalAgent(BaseExternalAgent):
    """A sample MCP-compliant external agent that runs as a separate service."""
    
    def __init__(self):
        super().__init__(
            name="MyNewExternalAgent",
            version="1.0.0",
            description="A sample external agent for demonstration",
            instructions="This agent can perform tasks when called by the Cogniscient system."
        )
        
        # Register the tools this agent exposes
        self.register_tool(
            "perform_task", 
            description="Perform a specific task", 
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "A sample parameter"}
                },
                "required": ["param1"]
            }
        )
    
    async def perform_task(self, ctx: Context, param1: str) -> str:
        """Perform the main task of the external agent."""
        # Use ctx for logging and context awareness
        await ctx.info(f"Performing task with param1: {param1}")
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

- An MCP-compliant server interface using the FastMCP framework
- Tool registration following MCP specifications
- Context-aware logging and progress reporting
- Automatic tool discovery through MCP protocol

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
8. **Tool Registration**: Use `register_tool()` to properly register your tools with JSON schemas
9. **MCP Compliance**: Make sure your methods are async and accept `Context` parameter for logging
10. **Context Logging**: Use the `ctx` parameter for logging with proper severity levels

### General:
11. **Documentation**: Document your agent's methods and parameters clearly
12. **Testing**: Create unit tests for your agents
13. **Security**: Validate all inputs to prevent injection attacks
14. **MCP Standards**: Follow MCP specifications for maximum interoperability