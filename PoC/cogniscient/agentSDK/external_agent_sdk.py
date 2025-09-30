"""
MCP-based SDK for building external agents.

This module provides utilities and helpers to make it easier to create
MCP-compliant external agents for the Cogniscient system.
"""

import inspect
from typing import Callable, Dict, Any
from mcp.server.fastmcp import Context
from cogniscient.agentSDK.base_external_agent import BaseExternalAgent


class AgentSDK:
    """
    A simple SDK to help create MCP-compliant external agents more easily.
    """
    
    @staticmethod
    def create_agent(name: str, 
                     version: str = "1.0.0", 
                     description: str = "",
                     instructions: str = "") -> BaseExternalAgent:
        """
        Create a new MCP-compliant external agent with the specified parameters.
        
        Args:
            name: Name of the agent
            version: Version of the agent
            description: Description of the agent's functionality
            instructions: Instructions for how the agent should be used
            
        Returns:
            A new BaseExternalAgent instance
        """
        return BaseExternalAgent(
            name=name,
            version=version,
            description=description,
            instructions=instructions
        )
    
    @staticmethod
    def register_function(agent: BaseExternalAgent, 
                         func: Callable, 
                         description: str = "",
                         input_schema: Dict[str, Any] = None,
                         auto_parameters: bool = True) -> None:
        """
        Register a function as a tool with the MCP agent.
        
        Args:
            agent: The agent to register the tool with
            func: The function to register (must be an async function that accepts ctx as first param)
            description: Description of what the function does
            input_schema: JSON schema describing the parameters (optional, auto-generated if not provided)
            auto_parameters: Whether to automatically detect parameters from function signature
        """
        func_name = func.__name__
        
        # Use provided schema or auto-generate
        if input_schema is None and auto_parameters:
            # Auto-detect parameters from function signature
            sig = inspect.signature(func)
            # Skip 'ctx' parameter which is the MCP Context
            params = [p for name, p in sig.parameters.items() if name != 'ctx']
            
            properties = {}
            required = []
            
            for param in params:
                param_info = {"type": "any", "description": f"Parameter {param.name}"}
                
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
                    required.append(param.name)
                
                properties[param.name] = param_info
            
            input_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }
        elif input_schema is None:
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        # Register the tool with the agent
        agent.register_tool(func_name, description or f"Tool: {func_name}", input_schema)
        
        # Add the function as a method to the agent
        setattr(agent, func_name, func)


def agent_tool(description: str = "", input_schema: Dict[str, Any] = None):
    """
    Decorator to mark a function as an agent tool.
    
    Args:
        description: Description of what the tool does
        input_schema: JSON schema for the tool's parameters
    """
    def decorator(func):
        # Store metadata about the function
        func._agent_tool = {
            "description": description,
            "input_schema": input_schema,
            "name": func.__name__
        }
        return func
    return decorator


class SimpleAgentBuilder:
    """
    A builder class to make creating MCP agents easier.
    """
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = "", instructions: str = ""):
        self.name = name
        self.version = version
        self.description = description
        self.instructions = instructions
        self.tools = {}
        
    def add_tool(self, name: str, func: Callable, description: str = "", input_schema: Dict[str, Any] = None, auto_parameters: bool = True):
        """Add a tool to the agent."""
        self.tools[name] = {
            "func": func,
            "description": description,
            "input_schema": input_schema,
            "auto_parameters": auto_parameters
        }
        return self
    
    def add_tools_from_class(self, cls):
        """Add all methods marked with @agent_tool from a class."""
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if hasattr(attr, '_agent_tool'):
                tool_info = attr._agent_tool
                self.add_tool(tool_info['name'], attr, 
                              tool_info['description'], 
                              tool_info['input_schema'])
        return self
    
    def build(self) -> BaseExternalAgent:
        """Build the agent with all configured tools."""
        agent = BaseExternalAgent(
            name=self.name,
            version=self.version,
            description=self.description,
            instructions=self.instructions
        )
        
        # Register all tools
        for name, tool_info in self.tools.items():
            func = tool_info['func']
            description = tool_info['description']
            input_schema = tool_info['input_schema']
            auto_parameters = tool_info['auto_parameters']
            
            # Register the tool with the agent
            AgentSDK.register_function(agent, func, description, input_schema, auto_parameters)
            
            # Add the function as a method to the agent
            setattr(agent, name, func)
        
        return agent


# Example usage:
if __name__ == "__main__":
    import asyncio
    
    # Example 1: Using the AgentSDK directly
    print("Example 1: Using AgentSDK directly")
    
    async def add_numbers(ctx: Context, a: float, b: float) -> float:
        """Add two numbers together."""
        await ctx.info(f"Adding {a} and {b}")
        return a + b
    
    async def get_greeting(ctx: Context, name: str, title: str = "Mr./Ms.") -> str:
        """Get a greeting for a person."""
        await ctx.info(f"Creating greeting for {name}")
        return f"Hello {title} {name}!"
    
    # Create an agent
    sdk_agent = AgentSDK.create_agent(
        name="SDKMathAgent",
        description="A math agent created with the SDK",
        instructions="This agent can perform basic mathematical operations and generate greetings."
    )
    
    # Register functions
    AgentSDK.register_function(sdk_agent, add_numbers, "Add two numbers together")
    AgentSDK.register_function(sdk_agent, get_greeting, "Get a greeting for a person")
    
    print(f"Registered tools: {sdk_agent.mcp._tool_manager._tools.keys() if hasattr(sdk_agent.mcp, '_tool_manager') else 'No tools registered yet'}")
    
    # Example 2: Using the SimpleAgentBuilder
    print("\nExample 2: Using SimpleAgentBuilder")
    
    async def multiply_numbers(ctx: Context, x: float, y: float) -> float:
        """Multiply two numbers."""
        await ctx.info(f"Multiplying {x} and {y}")
        return x * y
    
    async def reverse_string(ctx: Context, text: str) -> str:
        """Reverse the input string."""
        await ctx.info(f"Reversing string '{text}'")
        return text[::-1]
    
    builder_agent = (SimpleAgentBuilder("BuilderAgent", 
                                       description="An agent built with the builder",
                                       instructions="This agent can multiply numbers and reverse strings.")
                     .add_tool("multiply", multiply_numbers, "Multiply two numbers")
                     .add_tool("reverse", reverse_string, "Reverse the input string")
                     .build())
    
    print(f"Builder agent tools: {builder_agent.mcp._tool_manager._tools.keys() if hasattr(builder_agent.mcp, '_tool_manager') else 'No tools registered yet'}")
    
    # Example 3: Using the decorator approach
    print("\nExample 3: Using decorator approach")
    
    class CalculatorAgent:
        @agent_tool(description="Perform a calculation")
        async def calculate(self, ctx: Context, operation: str, a: float, b: float) -> float:
            """Perform a calculation based on the operation."""
            await ctx.info(f"Performing {operation} on {a} and {b}")
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
                    await ctx.error("Cannot divide by zero")
                    raise ValueError("Cannot divide by zero")
            else:
                await ctx.error(f"Unknown operation: {operation}")
                raise ValueError(f"Unknown operation: {operation}")
        
        @agent_tool(description="Get the square of a number")
        async def square(self, ctx: Context, x: float) -> float:
            """Get the square of a number."""
            await ctx.info(f"Squaring {x}")
            return x * x
    
    calc_agent = (SimpleAgentBuilder("CalculatorAgent", 
                                    description="A calculator agent",
                                    instructions="This agent can perform various mathematical calculations.")
                  .add_tools_from_class(CalculatorAgent())
                  .build())
    
    print(f"Calculator agent tools: {calc_agent.mcp._tool_manager._tools.keys() if hasattr(calc_agent.mcp, '_tool_manager') else 'No tools registered yet'}")