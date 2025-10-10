"""Sample agent B implementation - MCP-compliant version."""

import urllib.request
import urllib.error
import time
import random
from typing import Any, Dict, List


class SampleAgentB:
    """Sample agent B implementation with website checking capabilities, MCP-compliant."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the agent with configuration.
        
        Args:
            config: Agent configuration dictionary
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.runtime_ref = None
        self._tools_registered = False

    def register_mcp_tools(self):
        """Register tools with the MCP tool registry."""
        if not self.runtime_ref or not hasattr(self.runtime_ref, 'mcp_client_service'):
            print(f"Warning: No runtime reference for {self.name}, skipping tool registration")
            return

        # Register tools in MCP format to the tool registry
        mcp_client = self.runtime_ref.mcp_client_service

        # Register perform_website_check tool
        website_check_tool_desc = {
            "name": "sample_agent_b_perform_website_check",
            "description": "Check the status and gather diagnostics for a website or specific URI",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the website or specific URI to check. Can be a base URL (e.g., https://example.com) or a specific path (e.g., https://example.com/path/document)"
                    }
                },
                "required": []
            },
            "type": "function"
        }

        # Add to agent's tools in the registry
        agent_tools = mcp_client.tool_registry.get(self.name, [])
        agent_tools.append(website_check_tool_desc)
        mcp_client.tool_registry[self.name] = agent_tools

        # Register individual tool type
        mcp_client.tool_types[website_check_tool_desc["name"]] = False  # Not a system tool

        self._tools_registered = True

    def set_runtime(self, runtime_ref):
        """Set a reference to the runtime for this agent.
        
        Args:
            runtime_ref: Reference to the runtime
        """
        self.runtime_ref = runtime_ref
        # Register tools immediately if runtime is set
        if not self._tools_registered:
            self.register_mcp_tools()

    def perform_website_check(self, url: str = None) -> Dict[str, Any]:
        """Perform a website check with configurable behavior and detailed diagnostics.
        
        Args:
            url: URL to check. Defaults to website_settings.target_url.
            
        Returns:
            Result of the website check with status and relevant information.
        """
        # Apply response time delay if configured
        delay_ms = self.config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        # Possibly inject error based on error rate
        error_rate = self.config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise urllib.error.URLError("Simulated network error")

        # Use default settings if none provided
        url = url or self.config.get("website_settings", {}).get("target_url", "https://httpbin.org/delay/1")
        timeout = self.config.get("website_settings", {}).get("timeout", 10)

        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Cogniscient Website Checker/1.0')
            response = urllib.request.urlopen(request, timeout=timeout)

            # Collect additional diagnostic information
            headers = dict(response.headers)
            content_length = headers.get('Content-Length', 'Unknown')

            return {
                "status": "success", 
                "status_code": response.getcode(), 
                "response_time": response.headers.get('Date'),
                "content_length": content_length,
                "headers": headers
            }
        except urllib.error.HTTPError as e:
            # More specific error classification for HTTP errors
            if e.code == 404:
                error_type = "NOT_FOUND_ERROR"
                message = "Document not found (404): The requested URI does not exist on the server"
            elif e.code >= 500:
                error_type = "SERVER_ERROR"
                message = f"Server error ({e.code}): {e.reason}"
            else:
                error_type = "HTTP_ERROR"
                message = f"HTTP {e.code}: {e.reason}"
                
            return {
                "status": "error", 
                "message": message,
                "error_type": error_type,
                "status_code": e.code
            }
        except urllib.error.URLError as e:
            # More specific error classification
            error_msg = str(e)
            if "Name or service not known" in error_msg or "nodename nor servname provided" in error_msg:
                error_type = "DNS_ERROR"
            elif "timed out" in error_msg:
                error_type = "TIMEOUT_ERROR"
            elif "Network is unreachable" in error_msg:
                error_type = "NETWORK_ERROR"
            else:
                error_type = "CONNECTION_ERROR"
                
            return {
                "status": "error", 
                "message": error_msg,
                "error_type": error_type
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": str(e),
                "error_type": "UNKNOWN_ERROR"
            }