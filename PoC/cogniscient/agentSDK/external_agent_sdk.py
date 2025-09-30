"""
Simple SDK for building external agents.

This module provides utilities and helpers to make it easier to create
external agents for the UCS system.
"""

import inspect
from typing import Callable
from cogniscient.agentSDK.base_external_agent import BaseExternalAgent


class AgentSDK:
    """
    A simple SDK to help create external agents more easily.
    """
    
    @staticmethod
    def create_agent(name: str, 
                     version: str = "1.0.0", 
                     description: str = "",
                     host: str = "0.0.0.0", 
                     port: int = 8001) -> BaseExternalAgent:
        """
        Create a new external agent with the specified parameters.
        
        Args:
            name: Name of the agent
            version: Version of the agent
            description: Description of the agent's functionality
            host: Host address for the agent's API server
            port: Port for the agent's API server
            
        Returns:
            A new BaseExternalAgent instance
        """
        return BaseExternalAgent(
            name=name,
            version=version,
            description=description,
            host=host,
            port=port
        )
    
    @staticmethod
    def register_function(agent: BaseExternalAgent, 
                         func: Callable, 
                         description: str = "",
                         auto_parameters: bool = True) -> None:
        """
        Register a function as a method with the agent.
        
        Args:
            agent: The agent to register the method with
            func: The function to register
            description: Description of what the function does
            auto_parameters: Whether to automatically detect parameters from function signature
        """
        func_name = func.__name__
        
        if auto_parameters:
            # Auto-detect parameters from function signature
            sig = inspect.signature(func)
            parameters = {}
            
            for param_name, param in sig.parameters.items():
                param_info = {"type": "any", "description": f"Parameter {param_name}"}
                
                # Try to determine type from annotation
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == str:
                        param_info["type"] = "string"
                    elif param.annotation == int:
                        param_info["type"] = "integer"
                    elif param.annotation == float:
                        param_info["type"] = "number"
                    elif param.annotation == bool:
                        param_info["type"] = "boolean"
                    else:
                        param_info["type"] = str(param.annotation)
                
                # Check if parameter has a default value
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default
                else:
                    param_info["required"] = True
                
                parameters[param_name] = param_info
        else:
            parameters = {}
        
        # Register the method with the agent
        agent.register_method(func_name, description or f"Method: {func_name}", parameters)
        
        # Add the function as a method to the agent
        setattr(agent, func_name, func)


def agent_method(description: str = "", auto_parameters: bool = True):
    """
    Decorator to mark a function as an agent method.
    
    Args:
        description: Description of what the method does
        auto_parameters: Whether to automatically detect parameters from function signature
    """
    def decorator(func):
        # Store metadata about the function
        func._agent_method = {
            "description": description,
            "auto_parameters": auto_parameters,
            "name": func.__name__
        }
        return func
    return decorator


class SimpleAgentBuilder:
    """
    A builder class to make creating agents easier.
    """
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.host = "0.0.0.0"
        self.port = 8001
        self.methods = {}
        
    def set_host(self, host: str):
        """Set the host for the agent."""
        self.host = host
        return self
        
    def set_port(self, port: int):
        """Set the port for the agent."""
        self.port = port
        return self
    
    def add_method(self, name: str, func: Callable, description: str = "", auto_parameters: bool = True):
        """Add a method to the agent."""
        self.methods[name] = {
            "func": func,
            "description": description,
            "auto_parameters": auto_parameters
        }
        return self
    
    def add_methods_from_class(self, cls):
        """Add all methods marked with @agent_method from a class."""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_agent_method'):
                method_info = attr._agent_method
                self.add_method(method_info['name'], attr, 
                              method_info['description'], 
                              method_info['auto_parameters'])
        return self
    
    def build(self) -> BaseExternalAgent:
        """Build the agent with all configured methods."""
        agent = BaseExternalAgent(
            name=self.name,
            version=self.version,
            description=self.description,
            host=self.host,
            port=self.port
        )
        
        # Register all methods
        for name, method_info in self.methods.items():
            func = method_info['func']
            description = method_info['description']
            auto_parameters = method_info['auto_parameters']
            
            # Register the method with the agent
            AgentSDK.register_function(agent, func, description, auto_parameters)
            
            # Add the function as a method to the agent
            setattr(agent, name, func)
        
        return agent


# Example usage:
if __name__ == "__main__":
    # Example 1: Using the AgentSDK directly
    print("Example 1: Using AgentSDK directly")
    
    def add_numbers(a: float, b: float) -> float:
        """Add two numbers together."""
        return a + b
    
    def get_greeting(name: str, title: str = "Mr./Ms.") -> str:
        """Get a greeting for a person."""
        return f"Hello {title} {name}!"
    
    # Create an agent
    sdk_agent = AgentSDK.create_agent(
        name="SDKMathAgent",
        description="A math agent created with the SDK"
    )
    
    # Register functions
    AgentSDK.register_function(sdk_agent, add_numbers, "Add two numbers together")
    AgentSDK.register_function(sdk_agent, get_greeting, "Get a greeting for a person")
    
    print(f"Registered methods: {list(sdk_agent.methods.keys())}")
    
    
    # Example 2: Using the SimpleAgentBuilder
    print("\nExample 2: Using SimpleAgentBuilder")
    
    def multiply_numbers(x: float, y: float) -> float:
        """Multiply two numbers."""
        return x * y
    
    def reverse_string(text: str) -> str:
        """Reverse the input string."""
        return text[::-1]
    
    builder_agent = (SimpleAgentBuilder("BuilderAgent", description="An agent built with the builder")
                     .add_method("multiply", multiply_numbers, "Multiply two numbers")
                     .add_method("reverse", reverse_string, "Reverse the input string")
                     .build())
    
    print(f"Builder agent methods: {list(builder_agent.methods.keys())}")
    
    
    # Example 3: Using the decorator approach
    print("\nExample 3: Using decorator approach")
    
    class CalculatorAgent:
        @agent_method(description="Perform a calculation")
        def calculate(self, operation: str, a: float, b: float) -> float:
            """Perform a calculation based on the operation."""
            if operation == "add":
                return a + b
            elif operation == "subtract":
                return a - b
            elif operation == "multiply":
                return a * b
            elif operation == "divide":
                if b != 0:
                    return a / b
                else:
                    raise ValueError("Cannot divide by zero")
            else:
                raise ValueError(f"Unknown operation: {operation}")
        
        @agent_method(description="Get the square of a number")
        def square(self, x: float) -> float:
            """Get the square of a number."""
            return x * x
    
    calc_agent = (SimpleAgentBuilder("CalculatorAgent", description="A calculator agent")
                  .add_methods_from_class(CalculatorAgent())
                  .build())
    
    print(f"Calculator agent methods: {list(calc_agent.methods.keys())}")