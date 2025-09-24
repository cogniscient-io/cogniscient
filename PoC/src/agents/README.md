# External Agent SDK

This SDK provides tools and documentation for creating external agents that can be registered with the Universal Control System (UCS).

## Components

- **Base External Agent** (`base_external_agent.py`): A foundation class that handles the HTTP server and API contract
- **SDK Utilities** (`external_agent_sdk.py`): Helper classes and functions to simplify agent creation
- **Examples** (`example_agents.py`): Sample implementations to learn from
- **Documentation** (`docs/external-agent-sdk.md`): Complete guide to building external agents

## Getting Started

### 1. Quick Example

Here's how to create a simple external agent:

```python
from src.agents.external_agent_sdk import SimpleAgentBuilder

def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

# Create and configure the agent
agent = (SimpleAgentBuilder('MathAgent', description='A simple math agent')
         .add_method('add', add_numbers, 'Add two numbers together')
         .build())

# Run the agent
agent.run(host="0.0.0.0", port=8001)
```

### 2. Using Decorators

You can also use decorators to define agent methods:

```python
from src.agents.external_agent_sdk import SimpleAgentBuilder, agent_method

class CalculatorAgent:
    @agent_method(description="Multiply two numbers")
    def multiply(self, x: float, y: float) -> float:
        """Multiply two numbers."""
        return x * y
    
    @agent_method(description="Get the square of a number")
    def square(self, x: float) -> float:
        """Get the square of a number."""
        return x * x

# Create an agent with decorator-marked methods
agent = (SimpleAgentBuilder('CalculatorAgent', description='A calculator agent')
         .add_methods_from_class(CalculatorAgent())
         .build())

agent.run()
```

### 3. Registering with UCS

After starting your external agent, register it with UCS using the REST API:

```bash
curl -X POST "http://ucs-host:9001/api/agents/external/register" \\
     -H "Authorization: Bearer your-api-key" \\
     -H "Content-Type: application/json" \\
     -d '{
       "name": "YourAgentName",
       "description": "Your agent description",
       "version": "1.0.0",
       "endpoint_url": "http://your-agent-host:port",
       "methods": {
         "your_method": {
           "description": "Description of your method",
           "parameters": {}
         }
       }
     }'
```

## Documentation

For complete documentation, see [docs/external-agent-sdk.md](docs/external-agent-sdk.md).

## Examples

Check out the examples in `src/agents/example_agents.py` for more implementation ideas.