"""Sample agent A implementation."""

import socket
import time
import random
import dns.resolver
from agents.base import Agent


class SampleAgentA(Agent):
    """Sample agent A implementation with DNS lookup capabilities."""

    def __init__(self, config=None):
        """Initialize the agent with a configuration.
        
        Args:
            config (dict, optional): Configuration for the agent.
        """
        self.config = config or self.self_describe()

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration and methods.
        """
        return {
            "name": "SampleAgentA",
            "version": "1.0",
            "enabled": True,
            "methods": {
                "perform_dns_lookup": {
                    "description": "Perform a DNS lookup for a domain",
                    "parameters": {
                        "domain": {
                            "type": "string",
                            "description": "The domain to lookup",
                            "required": False
                        },
                        "dns_server": {
                            "type": "string",
                            "description": "The DNS server to use for the lookup",
                            "required": False
                        }
                    }
                }
            },
            "dns_settings": {
                "target_domain": "example.com",
                "dns_server": "8.8.8.8",
                "timeout": 5
            },
            "response_controls": {
                "delay_ms": 0,
                "error_rate": 0.0
            },
            "settings": {
                "timeout": 30,
                "retries": 3
            }
        }

    def perform_dns_lookup(self, domain=None, dns_server=None) -> dict:
        """Perform a DNS lookup with configurable behavior.
        
        Args:
            domain (str, optional): Domain to lookup. Defaults to dns_settings.target_domain.
            dns_server (str, optional): DNS server to use. Defaults to dns_settings.dns_server.
            
        Returns:
            dict: Result of the DNS lookup with status and relevant information.
        """
        # Apply response time delay if configured
        delay_ms = self.config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        # Possibly inject error based on error rate
        error_rate = self.config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise socket.gaierror("Simulated DNS error")
            
        # Perform actual DNS lookup using specified DNS server
        domain = domain or self.config["dns_settings"]["target_domain"]
        dns_server = dns_server or self.config["dns_settings"]["dns_server"]
        
        try:
            # Create a resolver and set the nameserver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            
            # Set timeout
            resolver.timeout = self.config["dns_settings"]["timeout"]
            resolver.lifetime = self.config["dns_settings"]["timeout"]
            
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