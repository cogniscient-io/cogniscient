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
from typing import Dict, Any, List, Optional
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import PromptObject

# Set up logging
logger = logging.getLogger(__name__)


class SystemContextBuilder:
    """
    Builder for system context that provides the AI model with
    information about its environment, capabilities, and available tools.
    """
    
    def __init__(self, mcp_client: MCPClient, kernel=None):
        """
        Initialize the system context builder.
        
        Args:
            mcp_client: MCP client for communicating with the MCP server
            kernel: Optional direct reference to the kernel instance for direct access to registry
        """
        self.mcp_client = mcp_client
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

    def get_formatted_prompt_with_model_style(self, prompt_type: str, model_name: str = None, **kwargs) -> str:
        """
        Get a formatted prompt based on the model style (XML vs JSON).
        
        Args:
            prompt_type: Type of prompt to retrieve (e.g., 'tool_usage_instructions')
            model_name: Name of the model to determine appropriate style
            **kwargs: Arguments for formatting the prompt
            
        Returns:
            Formatted prompt string based on model style
        """
        # Determine if we should use XML-style or JSON-style based on model
        use_xml_style = False
        if model_name:
            # Check for qwen3-coder or similar models that prefer XML-style
            if 'qwen' in model_name.lower() and ('-coder' in model_name.lower() or '3-coder' in model_name.lower()):
                use_xml_style = True
            # You can add more model detection logic here
        
        # Select the appropriate prompt based on model style
        if use_xml_style:
            if prompt_type == "tool_usage_instructions":
                prompt_data = self.prompts.get("tool_usage_instructions_xml", self.prompts.get("tool_usage_instructions", []))
            else:
                prompt_data = self.prompts.get(f"{prompt_type}_xml", self.prompts.get(prompt_type, []))
        else:
            prompt_data = self.prompts.get(f"{prompt_type}_json", self.prompts.get(prompt_type, []))
        
        return self._format_prompt(prompt_data, **kwargs)

    async def build_and_apply_system_context(self, prompt_obj: PromptObject, additional_context: str = None, model_name: str = None) -> bool:
        """
        Build system context with general information about capabilities and apply it to the prompt object.
        Supports model-specific tool call formats (XML vs JSON).

        Args:
            prompt_obj: The PromptObject to apply the system context to
            additional_context: Optional additional context to include
            model_name: Name of the model to determine appropriate tool call format

        Returns:
            Boolean indicating success or failure
        """
        try:
            # Build the system context with general guidance only (no more tool listings)
            system_context = self._format_prompt(self.prompts["base_message_with_tools"], tool_names="available through the tools API")

            # Add general guidance
            system_context += self._format_prompt(self.prompts["general_guidance"])

            # Add model-specific tool usage instructions
            tool_instructions = self.get_formatted_prompt_with_model_style("tool_usage_instructions", model_name=model_name)
            system_context += tool_instructions

            # Add tool guidance
            system_context += self._format_prompt(self.prompts["tool_guidance"])

            # Add any additional context if provided
            if additional_context:
                system_context += self._format_prompt(self.prompts["additional_context_format"], additional_context=additional_context)

            # Add the system context to the prompt object's conversation history
            prompt_obj.add_system_message(system_context)

            return True
        except Exception as e:
            logger.error(f"Error building and applying system context: {str(e)}")
            return False
    
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