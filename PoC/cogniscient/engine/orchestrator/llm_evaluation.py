"""Module for agent output evaluation functionality in LLM Orchestration Engine."""

import json
import logging
from typing import Dict, Any
from cogniscient.engine.services.contextual_llm_service import ContextualLLMService
from cogniscient.llm.llm_service import LLMService as ProviderManager  # For backward compatibility during transition

logger = logging.getLogger(__name__)


class LLMEvaluation:
    """Handles evaluation of agent outputs using LLM."""

    def __init__(self, llm_service: ContextualLLMService = None, provider_manager: ProviderManager = None):
        """Initialize the evaluation module with LLM service.
        
        Args:
            llm_service (ContextualLLMService): The contextual LLM service instance.
            provider_manager (ProviderManager): The provider manager instance for LLM operations.
        """
        # Initialize with provided service or create contextual service from provider manager
        if llm_service is not None:
            self.llm_service = llm_service
        elif provider_manager:
            from cogniscient.engine.services.contextual_llm_service import ContextualLLMService
            self.llm_service = ContextualLLMService(provider_manager=provider_manager)
        else:
            raise ValueError("Either llm_service or provider_manager must be provided")

    async def evaluate_agent_output(self, agent_name: str, output: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate agent output using LLM and determine next actions.
        
        Args:
            agent_name (str): Name of the agent that produced the output.
            output (Dict[str, Any]): The output from the agent.
            
        Returns:
            Dict[str, Any]: The evaluation result with next actions.
        """
        # Construct prompt for LLM evaluation
        prompt = f"Agent {agent_name} produced output: {json.dumps(output)}\n"
        prompt += "Based on this output, what should be the next steps?\n"
        prompt += "Please respond with a JSON object that has the following structure:\n"
        prompt += "{\n"
        prompt += '  "decision": "success|retry|failure",\n'
        prompt += '  "reasoning": "Explanation for the decision",\n'
        prompt += '  "retry_params": {"param_name": "param_value"} // Only include this if decision is "retry"\n'
        prompt += "}\n"
        prompt += "Use 'success' if the task completed successfully.\n"
        prompt += "Use 'retry' if the task should be retried, possibly with different parameters. When suggesting retry_params, consider adjusting timeout values or other relevant settings.\n"
        prompt += "Use 'failure' if the task cannot be completed successfully.\n"
        prompt += "IMPORTANT: Respond ONLY with the JSON object. Do not include any other text, markdown, or formatting.\n"
        
        try:
            # Get LLM evaluation using the contextual LLM service
            evaluation_result = await self.llm_service.generate_response(prompt, return_token_counts=True)
            
            # Handle the response based on whether token counts were returned
            if isinstance(evaluation_result, dict) and "token_counts" in evaluation_result:
                evaluation_text = evaluation_result["response"]
                token_counts = evaluation_result["token_counts"]
            else:
                evaluation_text = evaluation_result
                token_counts = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0
                }
            
            # Parse and validate the LLM response
            evaluation = self._parse_llm_json_response(evaluation_text)
            
            # Validate the structure of the evaluation
            if "decision" not in evaluation:
                evaluation["decision"] = "failure"
                evaluation["reasoning"] = f"Missing 'decision' field in LLM response: {evaluation}"
            
            # Add token counts to the evaluation result
            evaluation["token_counts"] = token_counts
            
            return evaluation
        except Exception as e:
            logger.error(f"Error evaluating agent output: {e}")
            return {"decision": "failure", "reasoning": f"Error in evaluation: {str(e)}"}

    def _parse_llm_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text that should contain a JSON object.
        
        Args:
            response_text (str): The raw text response from the LLM.
            
        Returns:
            Dict[str, Any]: The parsed JSON object, or an error object if parsing fails.
        """
        # Clean up the response text
        # Remove any markdown code block markers
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        # Try to parse as JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            # This handles cases where the LLM includes additional text around the JSON
            import re
            # Look for a JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    return {"error": f"Could not parse LLM response as JSON: {cleaned_text}"}
            else:
                return {"error": f"Could not find JSON in LLM response: {cleaned_text}"}
