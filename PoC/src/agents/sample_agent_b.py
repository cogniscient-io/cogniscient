"""Sample agent B implementation."""

import urllib.request
import urllib.error
import time
import random
from agents.base import Agent


class SampleAgentB(Agent):
    """Sample agent B implementation with website checking capabilities."""

    def self_describe(self) -> dict:
        """Return a dictionary describing the agent's capabilities.
        
        Returns:
            dict: A dictionary containing the agent's configuration.
        """
        return {
            "name": "SampleAgentB",
            "version": "1.0",
            "enabled": True,
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
        """Perform a website check with configurable behavior.
        
        Args:
            url (str, optional): URL to check. Defaults to website_settings.target_url.
            
        Returns:
            dict: Result of the website check with status and relevant information.
        """
        # Apply response time delay if configured
        config = self.self_describe()
        delay_ms = config.get("response_controls", {}).get("delay_ms", 0)
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        # Possibly inject error based on error rate
        error_rate = config.get("response_controls", {}).get("error_rate", 0.0)
        if error_rate > 0 and random.random() < error_rate:
            raise urllib.error.URLError("Simulated network error")
            
        # Perform actual website check
        url = url or config["website_settings"]["target_url"]
        try:
            response = urllib.request.urlopen(url, timeout=config["website_settings"]["timeout"])
            return {"status": "success", "status_code": response.getcode(), "response_time": response.headers.get('Date')}
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            return {"status": "error", "message": str(e)}