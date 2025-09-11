"""Sample agent A implementation."""

import socket
import time
import random
from agents.base import Agent


class SampleAgentA(Agent):
    """Sample agent A implementation with DNS lookup capabilities."""

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration.
        """
        return {
            "name": "SampleAgentA",
            "version": "1.0",
            "enabled": True,
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
        config = self.self_describe()
        delay_ms = config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        # Possibly inject error based on error rate
        error_rate = config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise socket.gaierror("Simulated DNS error")
            
        # Perform actual DNS lookup
        domain = domain or config["dns_settings"]["target_domain"]
        dns_server = dns_server or config["dns_settings"]["dns_server"]
        try:
            result = socket.getaddrinfo(domain, None)
            return {"status": "success", "addresses": [addr[4][0] for addr in result]}
        except socket.gaierror as e:
            return {"status": "error", "message": str(e)}