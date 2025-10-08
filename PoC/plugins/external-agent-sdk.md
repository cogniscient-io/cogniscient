# External Agent SDK Documentation - MCP Implementation

## Overview
This document provides guidelines and tools for developing external agents that can integrate with the Cogniscient Adaptive Control System using the Model Context Protocol (MCP). External agents are MCP-compliant services that run separately from the main application but can be dynamically registered and managed by the system through standardized tool interfaces.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Creating Your First MCP External Agent](#creating-your-first-mcp-external-agent)
3. [MCP Registration Process](#mcp-registration-process)
4. [MCP Tool Contract](#mcp-tool-contract)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

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

## Creating Your First MCP External Agent

To create an MCP-compliant external agent, you implement your tools directly through the Model Context Protocol (MCP) using the FastMCP framework:

```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context
from mcp.types import Tool
import asyncio
import json

# Create your MCP server directly with FastMCP
mcp = FastMCP(
    name="WeatherAgent",
    version="1.0.0",
    description="An agent that retrieves weather information",
)

# Register your tools using the @mcp.tool decorator
@mcp.tool(
    name="get_weather",
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
async def get_weather(ctx: Context, city: str, country_code: str) -> dict:
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

# Function to run the MCP server with different transports
def run_stdio():
    """Run the MCP server using stdio transport."""
    from mcp import stdio_server
    import asyncio
    
    async def run_server():
        async with stdio_server(mcp) as server:
            await server.join()  # Wait indefinitely for requests
    
    asyncio.run(run_server())

def run_http(host="127.0.0.1", port=8080):
    """Run the MCP server using streamable HTTP transport."""
    from mcp import http_server
    import asyncio
    
    async def run_server():
        async with http_server(mcp, host=host, port=port) as server:
            await server.join()  # Wait indefinitely for requests
    
    asyncio.run(run_server())

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "http":
            port = 8080
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid port {sys.argv[2]}, using default 8080")
                    port = 8080
            run_http(host="127.0.0.1", port=port)
        elif sys.argv[1] == "stdio":
            run_stdio()
        else:
            print(f"Unknown transport: {sys.argv[1]}")
            print("Usage: python your_agent.py [http|stdio] [port]")
    else:
        # Default to stdio transport
        run_stdio()
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

The HTTP transport will make your agent available as an HTTP service that can be accessed at the specified port. The HTTP transport uses the MCP Streamable HTTP protocol and will be available at `http://<host>:<port>/mcp`.

Note: The SSE transport is not directly supported in this simplified example but can be implemented using the appropriate MCP server functions.

## MCP Registration Process

Once your MCP external agent is running, it will automatically register its tools with the MCP client (Cogniscient system) through the standardized MCP protocol:

### 1. Automatic Tool Discovery
MCP agents automatically expose their available tools through the MCP discovery protocol. When you define tools using `@mcp.tool` decorator, they're automatically registered:

```python
# Tools defined with @mcp.tool are automatically available for discovery
# No special registration methods needed
```

### 2. MCP Client Integration
The Cogniscient system acts as an MCP client that connects to your external agent as an MCP server. The connection happens through standardized MCP transport (typically stdio, HTTP):

```python
from mcp.client import stdio_client, http_client

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
8. **Transport Selection**: Choose the appropriate transport (stdio for single use, HTTP for multiple clients)

## Examples

See the MCP-compliant agent implementations and the FastMCP documentation for complete examples of MCP server implementations that integrate with the LLM orchestrator.