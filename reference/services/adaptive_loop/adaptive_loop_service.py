"""
Adaptive Loop Service implementation for GCS Kernel.

This module implements the AdaptiveLoopService which intelligently
adapts to various situations by using AI to determine
appropriate solutions. This implements the Adaptive Loop concept.
"""

import logging
import re
from typing import Any, Dict, Optional
from gcs_kernel.mcp.client import MCPClient
from gcs_kernel.models import PromptObject
from services.ai_orchestrator.orchestrator_service import AIOrchestratorService


class AdaptiveLoopService:
    """
    AI-Assisted Adaptive Loop Service that intelligently adapts to various
    situations by using AI to determine appropriate solutions.
    """

    def __init__(self, mcp_client: MCPClient, ai_orchestrator: AIOrchestratorService):
        """
        Initialize the adaptive loop service.

        Args:
            mcp_client: MCP client for communicating with the kernel server
            ai_orchestrator: AI orchestrator service for processing requests
        """
        self.mcp_client = mcp_client
        self.ai_orchestrator = ai_orchestrator
        self.logger = logging.getLogger(__name__)

    async def adapt_async(
        self,
        context: Dict[str, Any],
        problem_description: str,
        fallback_value=None
    ) -> Any:
        """
        Adapt to a situation by using AI to find a solution.

        Args:
            context: Context data (e.g., model response) to analyze
            problem_description: Description of the specific problem to solve
            fallback_value: Value to return if AI processing fails

        Returns:
            AI-proposed solution or fallback value
        """
        # Create a PromptObject for the AI request with proper session isolation
        prompt_content = self._build_prompt(context, problem_description)
        self.logger.info(f"Adaptive Loop: Processing context for model {context.get('model_name', 'unknown')}")
        self.logger.debug(f"Adaptive Loop: AI prompt content: {prompt_content}")
        
        prompt_obj = PromptObject.create(
            content=prompt_content,
            streaming_enabled=False,
            user_id="adaptive_loop_service"  # Identify as kernel service
        )

        # Use the AI orchestrator to get the solution
        try:
            result = await self.ai_orchestrator.handle_ai_interaction(prompt_obj)
            if result.status.value == 'error':
                self.logger.warning(f"AI processing returned error: {result.error_message}, using fallback")
                return fallback_value
            
            self.logger.info(f"Adaptive Loop: AI response received: '{result.result_content}'")
            parsed_result = self._parse_ai_response(result.result_content)
            
            # If the AI explicitly said NOT_FOUND, return the fallback instead of None
            if parsed_result is None:
                self.logger.info(f"AI indicated the field was not found, using fallback: {fallback_value}")
                return fallback_value
            
            self.logger.info(f"Adaptive Loop: Successfully parsed AI response, extracted value: {parsed_result}")
            return parsed_result
        except Exception as e:
            # Log error and return fallback
            self.logger.warning(f"AI processing failed: {e}, using fallback")
            return fallback_value

    def _build_prompt(self, error_context: Dict[str, Any], problem_description: str) -> str:
        """
        Build an AI prompt based on the error context and problem description.

        Args:
            error_context: The context data to analyze
            problem_description: Description of the specific problem

        Returns:
            A formatted prompt string for the AI
        """
        return f"""Context: {error_context}

Problem: {problem_description}

Please analyze the context data and identify the most likely field that contains
the requested information. If you find a value, respond with the field name
and its value in the format: FIELD_NAME: VALUE

If the information is not available in the context, respond with "NOT_FOUND".
"""

    def _parse_ai_response(self, ai_response: str) -> Optional[str]:
        """
        Parse the AI response to extract the field and value.

        Args:
            ai_response: The raw response from the AI

        Returns:
            The value found in the AI response, or None if not found
        """
        # Look for the pattern "FIELD_NAME: VALUE" in the AI response
        # but be careful to avoid matching descriptive labels like "FIELD_NAME:" and "VALUE:"
        # Allow decimal numbers by using a more specific character class for the value
        matches = re.findall(r'(\w+):\s*([^\n\r,]+?)(?=\s*[,\n\r]|$)', ai_response, re.IGNORECASE)
        for field_name, value in matches:
            field_name = field_name.strip()
            value = value.strip()
            # Skip descriptive labels but process actual field names
            # Actual field names are things like "max_model_len", "max_tokens", etc.
            # Not "FIELD_NAME", "VALUE", "field", etc.
            if field_name.lower() not in ['field_name', 'value', 'field'] and not field_name.startswith('FIELD'):
                # If the value looks like a number, convert it
                try:
                    if '.' in value:
                        return float(value)
                    else:
                        return int(value)
                except ValueError:
                    return value.strip('"\'')  # Remove quotes if present

        # If the first pattern didn't work, look for any field_name: value pattern
        # but avoid the descriptive labels
        alt_pattern = r'(\w+):\s*([^\n\r]+?)(?=\s*$|[\n\r])'
        matches = re.findall(alt_pattern, ai_response)
        for field_name, value in matches:
            field_name = field_name.strip()
            value = value.strip()
            # Skip descriptive labels but process actual field names
            if field_name.lower() not in ['field_name', 'value', 'field'] and not field_name.startswith('FIELD'):
                # If the value looks like a number, convert it
                try:
                    if '.' in value:
                        return float(value)
                    else:
                        return int(value)
                except ValueError:
                    return value.strip('"\'')
        
        # If no clear match, just return the relevant part of the response
        # Remove common prefixes/suffixes and return the value
        cleaned_response = ai_response.strip()
        if cleaned_response.upper() == "NOT_FOUND":
            return None
            
        # As a last resort, try to find a number in the response
        number_match = re.search(r'(\d+(?:\.\d+)?)', cleaned_response)
        if number_match:
            num_str = number_match.group(1)
            try:
                if '.' in num_str:
                    return float(num_str)
                else:
                    return int(num_str)
            except ValueError:
                pass  # If conversion fails, continue to return string

        # If no number found, return the full cleaned response
        # (this might happen if the AI just returns the field name)
        return cleaned_response