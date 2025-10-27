"""
Content Converter for GCS Kernel LLM Provider Backend.

This module implements content conversion following ContentConverter patterns.
"""

import logging
from typing import Dict, Any
from services.llm_provider.base_converter import BaseConverter

# Set up logging
logger = logging.getLogger(__name__)


class OpenAIConverter(BaseConverter):
    """
    OpenAI-compatible converter for transforming data between kernel format and OpenAI provider format.
    This converter uses the base converter which already implements OpenAI-compatible functionality.
    """
    
    def __init__(self, model: str):
        super().__init__(model)
        
        # The base converter already handles OpenAI-compatible conversions
        # This class can be used to add any OpenAI-specific customizations if needed