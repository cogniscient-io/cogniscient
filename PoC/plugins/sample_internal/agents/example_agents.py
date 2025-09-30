"""
Example agents demonstrating how to use the BaseExternalAgent class.

This module provides examples of implementing custom external agents.
"""

from cogniscient.agentSDK.base_external_agent import BaseExternalAgent


class ExampleMathAgent(BaseExternalAgent):
    """
    Example math agent that demonstrates the usage of BaseExternalAgent.
    """


class TimeAgent(BaseExternalAgent):
    """
    Example agent that provides time-related functionality.
    """
    
    def __init__(self):
        super().__init__(
            name="TimeAgent",
            version="1.0.0",
            description="An agent that provides time-related information"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "get_current_time", 
            description="Get the current time", 
            parameters={}
        )
        
        self.register_method(
            "sleep", 
            description="Pause execution for specified seconds", 
            parameters={
                "seconds": {"type": "number", "description": "Number of seconds to sleep", "required": True}
            }
        )
    
    def get_current_time(self) -> str:
        """Get the current time."""
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logger.info(f"Returning current time: {current_time}")
        return current_time
    
    def sleep(self, seconds: float) -> str:
        """Pause execution for specified seconds."""
        self.logger.info(f"Sleeping for {seconds} seconds")
        time.sleep(seconds)
        return f"Slept for {seconds} seconds"


class EchoAgent(BaseExternalAgent):
    """
    Example agent that echoes back the input with some processing.
    """
    
    def __init__(self):
        super().__init__(
            name="EchoAgent",
            version="1.0.0",
            description="An agent that echoes back provided text with processing"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "echo", 
            description="Echo back the input text", 
            parameters={
                "text": {"type": "string", "description": "Text to echo", "required": True}
            }
        )
        
        self.register_method(
            "count_chars", 
            description="Count characters in the input text", 
            parameters={
                "text": {"type": "string", "description": "Text to count characters for", "required": True}
            }
        )
    
    def echo(self, text: str) -> str:
        """Echo back the input text."""
        self.logger.info(f"Echoing: {text}")
        return f"ECHO: {text}"
    
    def count_chars(self, text: str) -> int:
        """Count characters in the input text."""
        count = len(text)
        self.logger.info(f"Character count for '{text[:20]}...': {count}")
        return count


class AsyncExampleAgent(BaseExternalAgent):
    """
    Example agent demonstrating async operations.
    """
    
    def __init__(self):
        super().__init__(
            name="AsyncExampleAgent",
            version="1.0.0",
            description="An agent that demonstrates async operations"
        )
        
        # Register the methods this agent supports
        self.register_method(
            "fetch_data", 
            description="Simulate fetching data asynchronously", 
            parameters={
                "delay": {"type": "number", "description": "Delay in seconds", "required": False, "default": 1}
            }
        )
    
    async def fetch_data(self, delay: float = 1.0) -> dict:
        """Simulate fetching data asynchronously."""
        self.logger.info(f"Starting async fetch with {delay}s delay")
        await asyncio.sleep(delay)
        result = {
            "data": "some important data",
            "timestamp": time.time(),
            "delay_used": delay
        }
        self.logger.info(f"Completed async fetch: {result}")
        return result


if __name__ == "__main__":
    # Example: Run the TimeAgent
    agent = TimeAgent()
    agent.run(host="0.0.0.0", port=8002)