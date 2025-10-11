"""
Response Evaluator Service for Adaptive Control System that implements
the error-as-signal approach as part of the new LLM architecture.

This service evaluates responses, implements error-as-signal approach,
and manages the LLM processing loop.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from enum import Enum
from cogniscient.engine.services.service_interface import Service
from cogniscient.engine.services.llm.llm_provider_manager import LLMProviderManager
from cogniscient.engine.services.llm.prompt_construction_service import PromptConstructionService
from cogniscient.engine.config.settings import settings

logger = logging.getLogger(__name__)


class ErrorSignalType(Enum):
    """Types of error signals that can be detected in responses."""
    MODEL_ERROR = "model_error"
    CONTENT_ERROR = "content_error"
    CONTEXT_ERROR = "context_error"
    VALIDATION_ERROR = "validation_error"
    RETRY_ERROR = "retry_error"
    MCP_ERROR = "mcp_error"


class ResponseEvaluatorService(Service):
    """
    Service that evaluates responses, implements error-as-signal approach,
    and manages the LLM processing loop.
    """
    
    def __init__(self, 
                 llm_provider_manager: LLMProviderManager,
                 prompt_construction_service: PromptConstructionService,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 error_threshold: float = 0.7):
        """
        Initialize the response evaluator service.
        
        Args:
            llm_provider_manager: The LLM provider manager
            prompt_construction_service: Service for constructing prompts with context
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds
            error_threshold: Threshold for determining if a response is an error
        """
        self.llm_provider_manager = llm_provider_manager
        self.prompt_construction_service = prompt_construction_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_threshold = error_threshold
        self.gcs_runtime = None  # Will be set by runtime
        
        # Statistics for monitoring
        self.total_evaluations = 0
        self.error_signals_detected = 0
        self.errors_handled = 0
        self.responses_evaluated = 0
        
    async def initialize(self) -> bool:
        """
        Initialize the response evaluator service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        # Initialize dependent services if needed
        if hasattr(self.llm_provider_manager, 'initialize'):
            await self.llm_provider_manager.initialize()
        return True
    
    async def shutdown(self) -> bool:
        """
        Shutdown the response evaluator service.
        
        Returns:
            True if shutdown was successful, False otherwise
        """
        # Shutdown dependent services if needed
        if hasattr(self.llm_provider_manager, 'shutdown'):
            await self.llm_provider_manager.shutdown()
        return True

    async def evaluate_response(self, response: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate a response and determine if it contains errors or signals.
        
        Args:
            response: The response text to evaluate
            context: Additional context for evaluation
            
        Returns:
            Dictionary containing evaluation results
        """
        self.responses_evaluated += 1
        evaluation_result = {
            "is_valid": True,
            "error_signals": [],
            "confidence_score": 1.0,
            "suggested_actions": [],
            "needs_retry": False,
            "needs_context_update": False
        }
        
        # Check if response is None or empty
        if not response:
            evaluation_result["is_valid"] = False
            evaluation_result["error_signals"].append({
                "type": ErrorSignalType.MODEL_ERROR.value,
                "message": "Empty or None response from LLM"
            })
            return evaluation_result
        
        # Look for error indicators in the response
        error_indicators = [
            "error", "failed", "unsuccessful", "unable to", 
            "exception", "timeout", "not found", "not available"
        ]
        
        response_lower = response.lower()
        error_signals = []
        
        for indicator in error_indicators:
            if indicator in response_lower:
                error_signals.append({
                    "type": ErrorSignalType.CONTENT_ERROR.value,
                    "message": f"Detected error indicator '{indicator}' in response",
                    "indicator": indicator
                })
        
        # Determine confidence score based on error signals
        confidence_score = 1.0 - (len(error_signals) * 0.1)  # Reduce confidence for each error signal
        evaluation_result["confidence_score"] = max(0.0, confidence_score)
        
        # Check if confidence is below threshold
        if confidence_score < self.error_threshold:
            evaluation_result["is_valid"] = False
            evaluation_result["needs_retry"] = True
            evaluation_result["error_signals"].extend(error_signals)
        else:
            evaluation_result["error_signals"].extend(error_signals)
        
        # Additional context-specific validation
        if context:
            # Validate against expected response format or content
            expected_format = context.get("expected_format")
            if expected_format and expected_format not in response:
                evaluation_result["is_valid"] = False
                evaluation_result["needs_context_update"] = True
                evaluation_result["error_signals"].append({
                    "type": ErrorSignalType.VALIDATION_ERROR.value,
                    "message": f"Response does not match expected format: {expected_format}"
                })
        
        # Increment error signals counter
        if evaluation_result["error_signals"]:
            self.error_signals_detected += len(evaluation_result["error_signals"])
        
        self.total_evaluations += 1
        return evaluation_result

    async def process_with_error_signals(
        self,
        prompt: str,
        domain: Optional[str] = "general",
        max_retries_override: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a prompt through the LLM with error-as-signal implementation.
        
        Args:
            prompt: The input prompt to process
            domain: Domain context for the response
            max_retries_override: Override for max retries
            context: Additional context for processing and evaluation
            
        Returns:
            Dictionary containing the response and processing metadata
        """
        retries = max_retries_override if max_retries_override is not None else self.max_retries
        
        # Construct contextual messages using the prompt construction service
        messages = await self.prompt_construction_service.construct_contextual_messages(
            user_input=prompt,
            domain=domain
        )
        
        for attempt in range(retries + 1):
            try:
                # Generate response from LLM
                response = await self.llm_provider_manager.generate_response(
                    messages[0]["content"],  # Use the user message content
                    domain=domain
                )
                
                # Evaluate the response
                evaluation = await self.evaluate_response(response, context)
                
                # If response is valid, return it
                if evaluation["is_valid"]:
                    return {
                        "response": response,
                        "evaluation": evaluation,
                        "attempt": attempt + 1,
                        "success": True
                    }
                else:
                    logger.warning(f"Response evaluation failed on attempt {attempt + 1}: {evaluation['error_signals']}")
                    
                    # Check if we should retry based on evaluation
                    if not evaluation["needs_retry"] or attempt == retries:
                        # If we shouldn't retry or we've exhausted retries, return the response with error info
                        return {
                            "response": response,
                            "evaluation": evaluation,
                            "attempt": attempt + 1,
                            "success": False
                        }
                    
                    # Wait before retrying with exponential backoff
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    self.errors_handled += 1
            except Exception as e:
                logger.error(f"Error during LLM processing on attempt {attempt + 1}: {str(e)}")
                
                # Check if we have more retries
                if attempt == retries:
                    # Last attempt - return error
                    return {
                        "response": None,
                        "evaluation": {
                            "is_valid": False,
                            "error_signals": [{
                                "type": ErrorSignalType.MODEL_ERROR.value,
                                "message": f"Failed after {retries + 1} attempts: {str(e)}"
                            }],
                            "confidence_score": 0.0,
                            "suggested_actions": ["Check LLM provider connectivity", "Verify provider credentials"]
                        },
                        "attempt": attempt + 1,
                        "success": False
                    }
                
                # Wait before retrying with exponential backoff
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
                self.errors_handled += 1

    async def implement_error_as_signal(
        self,
        error: Exception,
        error_context: Optional[Dict[str, Any]] = None,
        response_handler: Optional[Callable[[str], Any]] = None
    ) -> Dict[str, Any]:
        """
        Implement the error-as-signal approach by treating errors as input for adaptation.
        
        Args:
            error: The error that occurred
            error_context: Additional context about the error
            response_handler: Optional handler for processed signals
            
        Returns:
            Dictionary containing the processed error signal and suggested actions
        """
        error_signal = {
            "type": ErrorSignalType.MODEL_ERROR.value,
            "message": str(error),
            "timestamp": asyncio.get_event_loop().time(),
            "context": error_context or {},
            "adaptation_suggestions": []
        }
        
        # Analyze the error and suggest adaptations
        error_str = str(error).lower()
        if "timeout" in error_str:
            error_signal["adaptation_suggestions"].append({
                "action": "increase_timeout",
                "description": "Consider increasing the timeout for this request",
                "severity": "medium"
            })
        elif "rate_limit" in error_str or "quota" in error_str:
            error_signal["adaptation_suggestions"].append({
                "action": "reduce_request_frequency",
                "description": "Slow down request frequency due to rate limiting",
                "severity": "high"
            })
        elif "invalid" in error_str or "auth" in error_str:
            error_signal["adaptation_suggestions"].append({
                "action": "verify_credentials",
                "description": "Verify provider credentials are valid",
                "severity": "high"
            })
        elif "connection" in error_str:
            error_signal["adaptation_suggestions"].append({
                "action": "check_connectivity",
                "description": "Check network connectivity to provider",
                "severity": "high"
            })
        
        # If a response handler is provided, process the error signal
        if response_handler:
            try:
                result = await response_handler(f"Error occurred: {error_signal['message']}. Suggestions: {error_signal['adaptation_suggestions']}")
                error_signal["response"] = result
            except Exception as handler_error:
                logger.error(f"Error in response handler: {handler_error}")
                error_signal["response"] = f"Error in response handler: {handler_error}"
        
        # Log the error signal for monitoring and potential system adaptation
        logger.warning(f"Error-as-signal implemented: {error_signal}")
        
        return error_signal

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the response evaluator service.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "total_evaluations": self.total_evaluations,
            "responses_evaluated": self.responses_evaluated,
            "error_signals_detected": self.error_signals_detected,
            "errors_handled": self.errors_handled,
            "error_rate": self.error_signals_detected / max(1, self.responses_evaluated)
        }

    def set_runtime(self, runtime):
        """
        Set the GCS runtime reference.
        
        Args:
            runtime: The GCS runtime instance.
        """
        self.gcs_runtime = runtime

    async def manage_llm_loop(
        self,
        input_stream: AsyncGenerator[str, None],
        domain: str = "general",
        on_response: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Manage a continuous LLM processing loop with error-as-signal implementation.
        
        Args:
            input_stream: Async generator providing input prompts
            domain: Domain context for all responses
            on_response: Optional callback for each response
        """
        async for prompt in input_stream:
            try:
                result = await self.process_with_error_signals(prompt, domain)
                
                # Call the response handler if provided
                if on_response:
                    on_response(result)
                
                # If errors were detected, potentially adapt the system
                if not result["success"] and result["evaluation"]["error_signals"]:
                    # Log error signals for potential system adaptation
                    logger.info(f"Error signals detected in loop: {result['evaluation']['error_signals']}")
                    
            except Exception as e:
                # Implement error-as-signal for exceptions in the loop
                error_signal = await self.implement_error_as_signal(e)
                logger.error(f"Error in LLM loop: {error_signal}")