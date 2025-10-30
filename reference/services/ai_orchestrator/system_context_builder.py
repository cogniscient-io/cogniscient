"""
System Context Builder for the GCS Kernel AI Orchestrator.

This module implements the SystemContextBuilder which constructs
system-level context for AI interactions, including available tools,
capabilities, and relevant context information.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List
from gcs_kernel.mcp.client import MCPClient

# Set up logging
logger = logging.getLogger(__name__)


class SystemContextBuilder:
    """
    Builder for system context that provides the AI model with
    information about its environment, capabilities, and available tools.
    """
    
    def __init__(self, kernel_client: MCPClient, kernel=None):
        """
        Initialize the system context builder.
        
        Args:
            kernel_client: MCP client for communicating with the kernel server
            kernel: Optional direct reference to the kernel instance for direct access to registry
        """
        self.kernel_client = kernel_client
        self.kernel = kernel
        self.prompts = self._load_prompts()
    
    def _load_prompts(self) -> Dict[str, Any]:
        """
        Load prompts from the prompts.json file.
        
        Returns:
            Dictionary containing the loaded prompts
        """
        # Get the directory where this module is located
        module_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_file_path = os.path.join(module_dir, 'prompts.json')
        
        try:
            with open(prompts_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)['system_context']
        except FileNotFoundError:
            # If prompts file is not found, return default prompts
            logger.warning(f"Prompts file {prompts_file_path} not found. Using default prompts.")
            return self._get_default_prompts()
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {prompts_file_path}. Using default prompts.")
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, Any]:
        """
        Get default prompts in case the file is not found or invalid.
        
        Returns:
            Dictionary containing default prompts
        """
        return {
            "base_message_with_tools": [
                "You are an AI assistant with specific capabilities in the GCS Kernel system.",
                "You have access to these tools: {tool_names}.",
                "",
                ""
            ],
            "available_tools_header": [
                "Available tools:",
                "",
                ""
            ],
            "tool_entry": [
                "- {tool_name}: {tool_description}",
                "{tool_parameters}",
                ""
            ],
            "parameter_format": [
                "  Parameters: {parameters}",
                ""
            ],
            "no_tools_message": [
                "You are an AI assistant with specific capabilities in the GCS Kernel system.",
                "",
                "No tools are currently available.",
                "",
                ""
            ],
            "tool_usage_instructions": [
                "When you need to use a tool, respond in JSON format with a tool_call object:",
                "{",
                '  "name": "tool_name",',
                "  \"arguments\": {",
                '    "param1": "value1",',
                '    "param2": "value2"',
                "  }",
                "}",
                "",
                ""
            ],
            "tool_guidance": [
                "Only use tools when necessary to fulfill the user's request.",
                "If a tool can help answer the user's question or perform a task,",
                "use it appropriately. Otherwise, respond directly to the user.",
                "",
                ""
            ],
            "additional_context_format": [
                "{additional_context}",
                "",
                ""
            ],
            "general_guidance": [
                "You are operating within the GCS Kernel system. Follow best practices for",
                "safety, security, and efficiency when executing tasks or using tools."
            ]
        }

    async def build_system_context(self, additional_context: str = None) -> str:
        """
        Build system context with general information about capabilities.
        Note: Specific tools are provided separately in the tools section of API requests,
        not in the system context, to avoid duplication.
        
        Args:
            additional_context: Optional additional context to include
            
        Returns:
            System context string with general guidance and capabilities
        """
        # Build the system context with general guidance only (no more tool listings)
        system_context = self._format_prompt(self.prompts["base_message_with_tools"], tool_names="available through the tools API")
        
        # Add general guidance
        system_context += self._format_prompt(self.prompts["general_guidance"])
        
        # Add any additional context if provided
        if additional_context:
            system_context += self._format_prompt(self.prompts["additional_context_format"], additional_context=additional_context)
        
        return system_context

    def _format_prompt(self, prompt_data, **kwargs) -> str:
        """
        Format a prompt by joining array elements with newlines and applying formatting.
        
        Args:
            prompt_data: Either a string or an array of strings
            **kwargs: Arguments to format into the string
            
        Returns:
            Formatted string with newlines joined and placeholders replaced
        """
        if isinstance(prompt_data, list):
            # Join array elements with newlines
            prompt_str = "\n".join(prompt_data)
        else:
            # It's already a string
            prompt_str = prompt_data
        
        # Apply formatting if kwargs are provided
        if kwargs:
            prompt_str = prompt_str.format(**kwargs)
        
        return prompt_str