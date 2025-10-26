"""
Base Converter for GCS Kernel LLM Provider Backend.

This module defines the abstract base converter interface that all
converter implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from gcs_kernel.models import ToolResult


class BaseConverter(ABC):
    """
    Abstract base class for content converters that transform data
    between kernel format and specific LLM provider format.
    """

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def convert_kernel_request_to_provider(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert kernel request format to provider-specific format.

        Args:
            request: Request in kernel format

        Returns:
            Request in provider-specific format
        """
        pass

    @abstractmethod
    def convert_provider_response_to_kernel(self, provider_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert provider response format to kernel format.

        Args:
            provider_response: Response from LLM provider (as dictionary)

        Returns:
            Response in kernel format
        """
        pass

    @abstractmethod
    def convert_kernel_tools_to_provider(self, kernel_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert kernel tool format to provider tool format.

        Args:
            kernel_tools: Tools in kernel format

        Returns:
            Tools in provider format
        """
        pass

    @abstractmethod
    def convert_kernel_tool_result_to_provider(self, tool_result: ToolResult) -> Dict[str, Any]:
        """
        Convert kernel ToolResult to provider format for continuing conversation.

        Args:
            tool_result: Tool result in kernel format

        Returns:
            Tool result in provider format
        """
        pass