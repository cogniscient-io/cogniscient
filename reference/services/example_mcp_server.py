"""
Compliant MCP Server Implementation for Development and Testing.

This module implements an MCP server compliant with the official specification
(version 2025-06-18) using JSON-RPC 2.0 over Server-Sent Events (SSE) with Streamable HTTP transport.
"""

import json
import asyncio
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from datetime import datetime


app = FastAPI(title="Compliant MCP Server", version="1.0.0")


# Store for tool executions and sessions
executions_store = {}
session_store = {}


def create_json_rpc_response(request_id: str, result: Any) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def create_json_rpc_error(request_id: str, code: int, message: str) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }


def format_sse_event(data: str) -> str:
    """Format data as an SSE event."""
    return f"data: {data}\n\n"


async def process_initialize_request(params: Dict[str, Any], request_id: str):
    """Process an 'initialize' request according to MCP specification."""
    # Create a session ID
    session_id = str(uuid.uuid4())
    
    # Store session info
    session_info = {
        "sessionId": session_id,
        "created": datetime.now().isoformat()
    }
    session_store[session_id] = session_info
    
    # Prepare the InitializeResult
    initialize_result = {
        "serverInfo": {
            "name": "Compliant MCP Server",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {
                "listChanged": False  # For this example, tools don't change dynamically
            }
        },
        "protocolVersion": "2025-06-18"
    }
    
    response = create_json_rpc_response(request_id, initialize_result)
    return response, session_id


async def process_list_tools_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/list' request."""
    tools = [
        {
            "name": "example_tool",
            "description": "An example tool for testing",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input for the example tool"
                    }
                },
                "required": ["input"]
            }
        },
        {
            "name": "date_tool",
            "description": "Returns the current date and time",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "echo_tool",
            "description": "Echoes back the input parameter",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    }
                },
                "required": ["message"]
            }
        }
    ]
    
    result = {"tools": tools}
    response = create_json_rpc_response(request_id, result)
    return response, None


async def process_get_tool_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/get' request."""
    tool_name = params.get("name")
    
    if tool_name == "example_tool":
        result = {
            "name": "example_tool",
            "description": "An example tool for testing",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Input for the example tool"
                    }
                },
                "required": ["input"]
            }
        }
    elif tool_name == "date_tool":
        result = {
            "name": "date_tool",
            "description": "Returns the current date and time",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    elif tool_name == "echo_tool":
        result = {
            "name": "echo_tool",
            "description": "Echoes back the input parameter",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    }
                },
                "required": ["message"]
            }
        }
    else:
        error_message = f"Tool '{tool_name}' not found"
        response = create_json_rpc_error(request_id, -32602, error_message)
        return response, None
    
async def process_tools_call_request(params: Dict[str, Any], request_id: str):
    """Process a 'tools/call' request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    # Simulate the tool execution
    if tool_name == "example_tool":
        input_value = arguments.get("input", "default")
        result = {
            "toolName": tool_name,
            "output": f"Example tool processed: {input_value}",
            "isError": False
        }
    elif tool_name == "date_tool":
        current_time = datetime.now().isoformat()
        result = {
            "toolName": tool_name,
            "output": f"Current date and time is: {current_time}",
            "isError": False
        }
    elif tool_name == "echo_tool":
        message = arguments.get("message", "")
        result = {
            "toolName": tool_name,
            "output": f"Echo: {message}",
            "isError": False
        }
    else:
        error_message = f"Tool '{tool_name}' not implemented"
        response = create_json_rpc_error(request_id, -32601, error_message)
        return response, None
    
    response = create_json_rpc_response(request_id, result)
    return response, None


async def handle_json_rpc_request(json_rpc_request: Dict[str, Any]):
    """Handle a JSON-RPC request based on its method."""
    method = json_rpc_request.get("method")
    request_id = json_rpc_request.get("id")  # This will be None for notifications
    params = json_rpc_request.get("params", {})
    
    # If it's a notification (no id), return empty response
    if request_id is None:
        return {}, None
    
    # Route the request to the appropriate handler
    try:
        if method == "initialize":
            return await process_initialize_request(params, request_id)
        elif method == "tools/list":
            return await process_list_tools_request(params, request_id)

        elif method == "tools/call":
            return await process_tools_call_request(params, request_id)
        elif method == "initialized":
            # This is a notification, just return empty response
            return {}, None
        else:
            # Unknown method
            response = create_json_rpc_error(request_id, -32601, f"Method not found: {method}")
            return response, None
    except Exception as e:
        response = create_json_rpc_error(request_id, -32603, f"Internal error: {str(e)}")
        return response, None


@app.post("/")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint that handles JSON-RPC requests and returns SSE responses."""
    # Get the body of the request
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    
    try:
        json_rpc_request = json.loads(body_str)
    except json.JSONDecodeError:
        error_response = create_json_rpc_error(None, -32700, "Parse error")
        content = format_sse_event(json.dumps(error_response))
        return StreamingResponse(
            iter([content]),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Important for SSE
            }
        )
    
    # Handle the JSON-RPC request
    response, session_id = await handle_json_rpc_request(json_rpc_request)
    
    # Create headers with session ID if it exists
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
        "X-Accel-Buffering": "no",  # Important for SSE
    }
    
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    
    # Prepare the response content
    async def event_generator():
        if response:
            yield format_sse_event(json.dumps(response))
    
    # Return the response as an SSE stream
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers
    )


@app.get("/")
async def root_handler():
    """Root handler for basic HTTP requests."""
    return {
        "message": "This is an MCP compliant server using JSON-RPC over Server-Sent Events",
        "protocol_version": "2025-06-18",
        "transport": "Streamable HTTP"
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info"
    )