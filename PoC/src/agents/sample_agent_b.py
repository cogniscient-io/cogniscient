"""Sample agent B implementation."""

import urllib.request
import urllib.error
import time
import random
from agents.base import Agent


class SampleAgentB(Agent):
    """Sample agent B implementation with website checking capabilities."""

    def __init__(self, config=None):
        """Initialize the agent with a configuration.
        
        Args:
            config (dict, optional): Configuration for the agent.
        """
        # Start with the self-describe definition as the base
        base_config = self.self_describe()
        
        # Merge with provided config, allowing config file to override defaults
        if config:
            # Update the base config with values from the config file
            for key, value in config.items():
                if isinstance(value, dict) and key in base_config and isinstance(base_config[key], dict):
                    # If both are dictionaries, merge them
                    base_config[key].update(value)
                else:
                    # Otherwise, replace the value
                    base_config[key] = value
        
        self.config = base_config

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration and methods.
        """
        return {
            "name": "SampleAgentB",
            "version": "1.0",
            "enabled": True,
            "methods": {
                "perform_website_check": {
                    "description": "Check the status and gather diagnostics for a website or specific URI",
                    "parameters": {
                        "url": {
                            "type": "string",
                            "description": "The URL of the website or specific URI to check. Can be a base URL (e.g., https://example.com) or a specific path (e.g., https://example.com/path/document)",
                            "required": False
                        }
                    }
                }
            },
            "website_settings": {
                "target_url": "https://httpbin.org/delay/1",
                "timeout": 10
            },
            "response_controls": {
                "delay_ms": 0,
                "error_rate": 0.0
            },
            "settings": {
                "timeout": 60,
                "retries": 5
            }
        }
    
    def perform_website_check(self, url=None) -> dict:
        """Perform a website check with configurable behavior and detailed diagnostics.
        
        Args:
            url (str, optional): URL to check. Defaults to website_settings.target_url.
            
        Returns:
            dict: Result of the website check with status and relevant information.
        """
        # Apply response time delay if configured
        delay_ms = self.config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        # Possibly inject error based on error rate
        error_rate = self.config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise urllib.error.URLError("Simulated network error")
            
        # Perform actual website check
        url = url or self.config["website_settings"]["target_url"]
        try:
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'Cogniscient Website Checker/1.0')
            response = urllib.request.urlopen(request, timeout=self.config["website_settings"]["timeout"])
            
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
                message = f"Document not found (404): The requested URI does not exist on the server"
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