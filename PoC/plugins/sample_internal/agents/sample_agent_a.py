"""Sample agent A implementation - MCP-compliant version."""

import socket
import time
import random
import dns.resolver
from typing import Any, Dict, List


class SampleAgentA:
    """Sample agent A implementation with DNS lookup capabilities, MCP-compliant."""

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

        # Register perform_dns_lookup tool
        dns_tool_desc = {
            "name": "sample_agent_a_perform_dns_lookup",
            "description": "Perform a DNS lookup for a domain",
            "input_schema": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain to lookup"
                    },
                    "dns_server": {
                        "type": "string",
                        "description": "The DNS server to use for the lookup"
                    }
                },
                "required": []
            },
            "type": "function"
        }

        # Add to agent's tools in the registry
        agent_tools = mcp_client.tool_registry.get(self.name, [])
        agent_tools.append(dns_tool_desc)
        mcp_client.tool_registry[self.name] = agent_tools

        # Register individual tool type
        mcp_client.tool_types[dns_tool_desc["name"]] = False  # Not a system tool

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

    def perform_dns_lookup(self, domain: str = None, dns_server: str = None) -> Dict[str, Any]:
        """Perform a DNS lookup with configurable behavior.
        
        Args:
            domain: Domain to lookup. Defaults to dns_settings.target_domain.
            dns_server: DNS server to use. Defaults to dns_settings.dns_server.
            
        Returns:
            Result of the DNS lookup with status and relevant information.
        """
        # Apply response time delay if configured
        delay_ms = self.config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        # Possibly inject error based on error rate
        error_rate = self.config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise socket.gaierror("Simulated DNS error")

        # Use default settings if none provided
        domain = domain or self.config.get("dns_settings", {}).get("target_domain", "example.com")
        dns_server = dns_server or self.config.get("dns_settings", {}).get("dns_server", "8.8.8.8")
        timeout = self.config.get("dns_settings", {}).get("timeout", 5)

        try:
            # Create a resolver and set the nameserver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]

            # Set timeout
            resolver.timeout = timeout
            resolver.lifetime = timeout

            # Perform the DNS query
            result = resolver.resolve(domain, 'A')
            addresses = [str(ip) for ip in result]
            return {"status": "success", "addresses": addresses}
        except dns.resolver.NXDOMAIN:
            return {"status": "error", "message": f"Domain {domain} does not exist"}
        except dns.resolver.Timeout:
            return {"status": "error", "message": f"Timeout while querying DNS server {dns_server}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}