# External Agent SDK Documentation - MCP Implementation

## Overview
This document provides guidelines and tools for developing external agents that can integrate with the Cogniscient Adaptive Control System using the Model Context Protocol (MCP). External agents are MCP-compliant services that run separately from the main application but can be dynamically registered and managed by the system through standardized tool interfaces.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Base External Agent](#base-external-agent)
3. [Creating Your First MCP External Agent](#creating-your-first-mcp-external-agent)
4. [MCP Registration Process](#mcp-registration-process)
5. [MCP Tool Contract](#mcp-tool-contract)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

## Getting Started

### Prerequisites
- Python 3.8+
- modelcontextprotocol
- The Cogniscient system for registration

### Installation
To get started, install the required dependencies:

```bash
pip install modelcontextprotocol
```

## Base External Agent

The `BaseExternalAgent` class provides a foundation for creating MCP-compliant external agents. It handles:
- MCP server setup using FastMCP
- Tool registration and schema validation
- Standardized tool discovery
- Context-aware tool interactions
- Logging

### Key Methods

#### `__init__(self, name, version, description, instructions)`
Initialize the MCP external agent with basic metadata.

Parameters:
- `name` (str): Name of the agent
- `version` (str): Version of the agent (default: "1.0.0")
- `description` (str): Description of the agent's functionality
- `instructions` (str): Instructions for how the agent should be used

#### `register_tool(self, name, description, input_schema)`
Register a tool with the agent to make it available for LLM-driven calls.

Parameters:
- `name` (str): Name of the tool (should be unique)
- `description` (str): Description of what the tool does
- `input_schema` (dict): JSON schema describing the parameters the tool accepts

#### `run(self, transport="stdio")`
Run the MCP external agent server synchronously.

Parameters:
- `transport` (str): Transport protocol to use ("stdio", "sse", or "streamable-http"). Default is "stdio".

#### `run_async(self)`
Run the MCP external agent server asynchronously.

#### `run_http_server(self, host="127.0.0.1", port=8080)`
Run the MCP external agent as an HTTP server using streamable HTTP transport.

Parameters:
- `host` (str): Host address for the HTTP server (default: "127.0.0.1")
- `port` (int): Port for the HTTP server (default: 8080)

#### `run_sse_server(self, host="127.0.0.1", port=8080, mount_path="/")`
Run the MCP external agent using Server-Sent Events (SSE) transport.

Parameters:
- `host` (str): Host address for the SSE server (default: "127.0.0.1")
- `port` (int): Port for the SSE server (default: 8080)
- `mount_path` (str): Mount path for the SSE endpoints (default: "/")

#### `get_mcp_registration_info(self)`
Get the MCP registration information needed for tool discovery and management.

## Creating Your First MCP External Agent

To create an MCP-compliant external agent, inherit from `BaseExternalAgent` and implement your specific tools:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from mcp.types import Tool
from cogniscient.agentSDK.base_external_agent import BaseExternalAgent
import requests

class WeatherAgent(BaseExternalAgent):
    def __init__(self):
        super().__init__(
            name="WeatherAgent",
            version="1.0.0",
            description="An agent that retrieves weather information",
            instructions="Use this agent to get current weather information for various locations."
        )
        
        # Register the tools this agent supports
        self.register_tool(
            "get_weather", 
            description="Get current weather for a location", 
            input_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "country_code": {"type": "string", "description": "Country code"}
                },
                "required": ["city", "country_code"]
            }
        )
    
    async def get_weather(self, ctx: Context, city: str, country_code: str) -> dict:
        """Get current weather for a location."""
        try:
            # Implementation would make API calls to weather service
            result = {
                "city": city,
                "country": country_code,
                "temperature": 22.5,
                "description": "Partly cloudy"
            }
            await ctx.info(f"Weather data retrieved for {city}, {country_code}")
            return result
        except Exception as e:
            await ctx.error(f"Error retrieving weather: {str(e)}")
            raise

if __name__ == "__main__":
    import sys
    agent = WeatherAgent()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "http":
            port = 8080
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid port {sys.argv[2]}, using default 8080")
                    port = 8080
            agent.run_http_server(host="127.0.0.1", port=port)
        elif sys.argv[1] == "sse":
            port = 8080
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid port {sys.argv[2]}, using default 8080")
                    port = 8080
            agent.run_sse_server(host="127.0.0.1", port=port)
        elif sys.argv[1] == "stdio":
            agent.run(transport="stdio")
        else:
            print(f"Unknown transport: {sys.argv[1]}")
            print("Usage: python your_agent.py [http|sse|stdio] [port]")
    else:
        # Default to stdio transport
        agent.run(transport="stdio")
```

## Running External Agents with HTTP Support

Your MCP external agents now support multiple transport mechanisms:

### STDIO Transport (Default)
```bash
python your_agent.py stdio
```

### HTTP Transport (Streamable HTTP)
```bash
python your_agent.py http          # Uses default port 8080
python your_agent.py http 8090     # Uses custom port 8090
```

### SSE Transport (Server-Sent Events)
```bash
python your_agent.py sse           # Uses default port 8080
python your_agent.py sse 8090      # Uses custom port 8090
```

The HTTP and SSE transports will make your agent available as an HTTP service that can be accessed at the specified port. The HTTP transport uses the MCP Streamable HTTP protocol and will be available at `http://<host>:<port>/mcp`.

## MCP Registration Process

Once your MCP external agent is running, it will automatically register its tools with the MCP client (Cogniscient system) through the standardized MCP protocol:

### 1. Automatic Tool Discovery
MCP agents automatically expose their available tools through the MCP discovery protocol. The `get_mcp_registration_info` method can be used to understand the tool registration:

```python
agent = YourMCPAgent()
registration_info = agent.get_mcp_registration_info()
```

### 2. MCP Client Integration
The Cogniscient system acts as an MCP client that connects to your external agent as an MCP server. The connection happens through standardized MCP transport (typically stdio, HTTP or WebSocket):

```python
from mcp.client import StdioClient

# The Cogniscient system will automatically discover and connect to your MCP server
# Tools will be available for LLM orchestration through the MCP protocol
```

### 3. Tool Usage by LLM
Once registered through MCP, tools become available for the LLM orchestrator:

```python
# The LLM can automatically decide to call your tools based on their descriptions
# and the current context, following the MCP standard for tool discovery
```

## MCP Tool Contract

MCP external agents must implement the following MCP protocol contract:

### MCP Standard Compliance

- Standardized tool discovery through `tools/list` endpoint
- Standardized tool calling through `tools/call` endpoint
- JSON Schema validation for all tool inputs
- Standardized error handling following MCP specifications
- Context logging with severity levels

### Tool Calling Format

When the Cogniscient system calls a tool on your MCP agent, it follows the MCP JSON-RPC format:
```json
{
  "method": "tools/call",
  "params": {
    "name": "weather_agent.get_weather",
    "arguments": {
      "city": "New York",
      "country_code": "US"
    }
  }
}
```

### Response Format

Your MCP agent should return responses following the MCP standard:

Success:
```json
{
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{ \"temperature\": 22.5, \"condition\": \"Partly cloudy\" }"
      }
    ]
  }
}
```

Error:
```json
{
  "error": {
    "code": 400,
    "message": "Invalid parameters",
    "data": {
      "description": "Error details"
    }
  }
}
```

### Context Logging

MCP agents can send logging messages to the client:

- `ctx.info(message)` - Log informational messages
- `ctx.warn(message)` - Log warnings
- `ctx.error(message)` - Log errors
- `ctx.progress(token)` - Report progress

## Best Practices

1. **Error Handling**: Always wrap tool calls in try-catch blocks and use ctx.error() to log errors
2. **Context Logging**: Use the provided Context object (ctx) for logging with proper severity levels
3. **Async Operations**: MCP tools should be async functions to support non-blocking operations
4. **Tool Naming**: Use clear, descriptive names for your tools that indicate their purpose
5. **Schema Validation**: Properly define JSON schemas for tool parameters to enable validation
6. **Security**: Implement proper authentication and validation as MCP servers may receive requests from multiple clients
7. **MCP Compliance**: Follow the Model Context Protocol specification for maximum interoperability

## Examples

See the MCP-compliant agent implementations in the Cogniscient system for complete examples of MCP server implementations that integrate with the LLM orchestrator.