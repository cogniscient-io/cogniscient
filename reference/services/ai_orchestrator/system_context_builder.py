"""
System Context Builder for the GCS Kernel AI Orchestrator.

This module implements the SystemContextBuilder which constructs
system-level context for AI interactions, including available tools,
capabilities, and relevant context information.
"""

import json
import logging
import os
from typing import Dict, Any
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
        self._default_prompts = self._load_prompts()
        self.prompts = self._default_prompts.copy()

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

        # For model-specific formatting, only use base prompts (tool format is system-level)
        # Domain data should not override the fundamental tool calling format
        prompt_data = self.prompts.get(prompt_type)

        # If prompt_data is a dict with 'json' and 'xml' keys, get the appropriate one
        if isinstance(prompt_data, dict):
            if use_xml_style:
                prompt_data = prompt_data.get('xml', [])
            else:
                prompt_data = prompt_data.get('json', [])
        elif prompt_data is None:
            # If the prompt type doesn't exist, default to empty list
            prompt_data = []

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
            # Build the system context with base message and tools
            system_context = self._format_prompt(self.prompts["base_message_with_tools"], tool_names="available through the tools API")

            # Add domain-specific information if available
            domain_data = self.get_domain_data()
            if domain_data and domain_data.get("domain_specific_info"):
                system_context += self._format_prompt(domain_data["domain_specific_info"])
                
            # Add tool usage rules
            if "tool_usage_rules" in self.prompts:
                system_context += self._format_prompt(self.prompts["tool_usage_rules"])

            # Add tool call format contract
            if "tool_call_format_contract" in self.prompts:
                system_context += self._format_prompt(self.prompts["tool_call_format_contract"])

            # Add model-specific tool usage instructions
            tool_instructions = self.get_formatted_prompt_with_model_style("tool_usage_instructions", model_name=model_name)
            system_context += tool_instructions

            # Add any additional context if provided
            if additional_context:
                system_context += self._format_prompt(self.prompts["additional_context_format"], additional_context=additional_context)

            # Add the system context to the prompt object's conversation history
            prompt_obj.add_system_message(system_context)

            return True
        except Exception as e:
            logger.error(f"Error building and applying system context: {str(e)}")
            return False

    def get_domain_data(self) -> Dict[str, Any]:
        """
        Get domain-specific data from the current domain context.
        This method looks for domain-specific prompts in the kernel or through the MCP client.

        Returns:
            Dictionary containing domain-specific data, or empty dict if not available
        """
        try:
            # If kernel is available, try to get the current domain from kernel state
            if self.kernel:
                # Look for domain information in kernel's context
                if hasattr(self.kernel, 'current_domain') and self.kernel.current_domain:
                    domain_path = self.kernel.current_domain

                    # Try to load domain-specific prompts from the domain directory
                    domain_prompts_path = os.path.join(domain_path, 'prompts.json')
                    if os.path.exists(domain_prompts_path):
                        with open(domain_prompts_path, 'r', encoding='utf-8') as f:
                            domain_data = json.load(f)
                            return domain_data.get('system_context', {})

            # If kernel or domain is not available, return empty dict
            return {}
        except Exception as e:
            logger.warning(f"Could not load domain data: {str(e)}")
            return {}

    def _get_default_prompts(self) -> Dict[str, Any]:
        """
        Get default prompts in case the file is not found or invalid.

        Returns:
            Dictionary containing default prompts
        """
        return {
            "base_message_with_tools": [
                "You are an AI assistant with specific capabilities in the GCS Kernel system specializing in software engineering tasks.",
                "Your primary goal is to help users safely and efficiently.",
                "You have access to these tools: {tool_names}.",
                "Use tools strategically and only when necessary to fulfill substantive requests."
            ],
            "tool_usage_rules": [
                "CRITICAL TOOL USAGE RULES:",
                "- DO NOT use tools for greetings, casual conversation, or simple acknowledgments like 'hello', 'hi', 'thanks', etc.",
                "- DO NOT use tools for general questions that can be answered with common knowledge.",
                "- ONLY use tools when the user specifically requests information that requires accessing files, code, system resources, or performing actions.",
                "- If a user's request is conversational or could be answered directly, respond without using any tools."
            ],
            "tool_call_format_contract": [
                "TOOL CALL FORMAT CONTRACT:",
                "- When you decide to use a tool, you must respond with an assistant message where 'content' is null and 'tool_calls' is an array.",
                "- DO NOT describe the tool call in plain text, XML, or Markdown.",
                "- DO NOT add any explanatory text or additional content when making tool calls.",
                "- DO NOT make up parameter values. If the user did not provide required parameters, respond with a message asking for the required information.",
                "If you are answering directly without tools, respond with an assistant message containing only 'content'."
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
                "You are an AI assistant with specific capabilities in the GCS Kernel system specializing in software engineering tasks.",
                "Your primary goal is to help users safely and efficiently.",
                "",
                "CRITICAL TOOL USAGE RULES:",
                "- DO NOT use tools for greetings, casual conversation or simple acknowledgments like 'hello', 'hi', 'thanks', etc.",
                "- DO NOT use tools for general questions that can be answered with common knowledge",
                "- ONLY use tools when the user specifically requests information that requires accessing files, code, system resources, or performing actions",
                "- If a user's request is conversational or could be answered directly, respond without using any tools",
                "",
                "No tools are currently available.",
                "",
                ""
            ],
            "tool_usage_instructions": {
                "json": [
                    "When you need to use a tool, respond in JSON format with a tool_call object:",
                    "{",
                    "  \"name\": \"tool_name\",",
                    "  \"arguments\": {",
                    "    \"param1\": \"value1\",",
                    "    \"param2\": \"value2\"",
                    "  }",
                    "}",
                    "",
                    ""
                ],
                "xml": [
                    "Use XML-style tags to call functions. Format your response with  tags:",
                    "",
                    "           ",
                    "",
                    ""
                ]
            },
            "additional_context_format": [
                "{additional_context}",
                "",
                ""
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