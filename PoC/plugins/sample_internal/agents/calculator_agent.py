"""
Calculator agent - MCP-compliant version.
"""

from typing import Any, Dict, List


class CalculatorAgent:
    """
    Calculator agent that demonstrates MCP-compliant local agent implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the agent with configuration.
        
        Args:
            config: Agent configuration dictionary
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        self.runtime_ref = None
        self._tools_registered = False
    
    def register_mcp_tools(self):
        """
        Register tools with the MCP tool registry.
        This is the MCP-compatible registration method.
        """
        if not self.runtime_ref or not hasattr(self.runtime_ref, 'mcp_client_service'):
            print(f"Warning: No runtime reference for {self.name}, skipping tool registration")
            return
        
        # Register tools in MCP format to the tool registry
        mcp_client = self.runtime_ref.mcp_client_service
        
        # Register add tool
        add_tool_desc = {
            "name": "calculator_agent_add",
            "description": "Add two numbers together",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"}
                },
                "required": ["a", "b"]
            },
            "type": "function"
        }
        
        # Register subtract tool
        subtract_tool_desc = {
            "name": "calculator_agent_subtract",
            "description": "Subtract the second number from the first",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"}
                },
                "required": ["a", "b"]
            },
            "type": "function"
        }
        
        # Register multiply tool
        multiply_tool_desc = {
            "name": "calculator_agent_multiply",
            "description": "Multiply two numbers",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"}
                },
                "required": ["a", "b"]
            },
            "type": "function"
        }
        
        # Register divide tool
        divide_tool_desc = {
            "name": "calculator_agent_divide",
            "description": "Divide the first number by the second",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number (dividend)"},
                    "b": {"type": "number", "description": "The second number (divisor)"}
                },
                "required": ["a", "b"]
            },
            "type": "function"
        }
        
        # Add to agent's tools in the registry
        agent_tools = mcp_client.tool_registry.get(self.name, [])
        agent_tools.extend([add_tool_desc, subtract_tool_desc, multiply_tool_desc, divide_tool_desc])
        mcp_client.tool_registry[self.name] = agent_tools
        
        # Also register individual tool types
        for tool_desc in [add_tool_desc, subtract_tool_desc, multiply_tool_desc, divide_tool_desc]:
            mcp_client.tool_types[tool_desc["name"]] = False  # Not a system tool
        
        self._tools_registered = True
    
    def set_runtime(self, runtime_ref):
        """
        Set a reference to the runtime for this agent.
        
        Args:
            runtime_ref: Reference to the runtime
        """
        self.runtime_ref = runtime_ref
        # Register tools immediately if runtime is set
        if not self._tools_registered:
            self.register_mcp_tools()
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers together."""
        result = a + b
        print(f"Calculated: {a} + {b} = {result}")
        return result
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract the second number from the first."""
        result = a - b
        print(f"Calculated: {a} - {b} = {result}")
        return result
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        result = a * b
        print(f"Calculated: {a} * {b} = {result}")
        return result
    
    def divide(self, a: float, b: float) -> float:
        """Divide the first number by the second."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        print(f"Calculated: {a} / {b} = {result}")
        return result