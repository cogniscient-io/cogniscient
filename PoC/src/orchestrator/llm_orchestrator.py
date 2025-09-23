"""LLM Orchestration Engine for Adaptive Control System."""

import json
import logging
from typing import Dict, Any, List
from src.services.llm_service import LLMService
from src.services.contextual_llm_service import ContextualLLMService
from src.ucs_runtime import UCSRuntime

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM Orchestration Engine for managing agents and their adaptations."""

    def __init__(self, ucs_runtime: UCSRuntime):
        """Initialize the LLM orchestrator with UCS runtime.
        
        Args:
            ucs_runtime (UCSRuntime): The UCS runtime instance to manage agents.
        """
        self.ucs_runtime = ucs_runtime
        # Use the LLM service from UCS runtime directly
        self.llm_service = ucs_runtime.llm_service
        self.parameter_ranges: Dict[str, Dict[str, Dict[str, Any]]] = {}  # Define acceptable parameter ranges
        self.approval_thresholds: Dict[str, Dict[str, Any]] = {}  # Define thresholds for human approval

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
            evaluation_text = await self.llm_service.generate_response(prompt)
            
            # Parse and validate the LLM response
            evaluation = self._parse_llm_json_response(evaluation_text)
            
            # Validate the structure of the evaluation
            if "decision" not in evaluation:
                evaluation["decision"] = "failure"
                evaluation["reasoning"] = f"Missing 'decision' field in LLM response: {evaluation}"
            
            return evaluation
        except Exception as e:
            logger.error(f"Error evaluating agent output: {e}")
            return {"decision": "failure", "reasoning": f"Error in evaluation: {str(e)}"}

    def is_within_range(self, agent_name: str, param: str, value: Any) -> bool:
        """Check if a parameter value is within the acceptable range.
        
        Args:
            agent_name (str): Name of the agent.
            param (str): Parameter name.
            value (Any): Parameter value to check.
            
        Returns:
            bool: True if value is within range, False otherwise.
        """
        if agent_name not in self.parameter_ranges:
            return True  # No ranges defined, allow all values
            
        agent_ranges = self.parameter_ranges[agent_name]
        if param not in agent_ranges:
            return True  # No range defined for this parameter, allow all values
            
        param_range = agent_ranges[param]
        min_val = param_range.get("min")
        max_val = param_range.get("max")
        
        # Check if value is within range
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    async def adapt_parameters(self, agent_name: str, suggested_changes: Dict[str, Any]) -> bool:
        """Adapt agent parameters within predefined ranges.
        
        Args:
            agent_name (str): Name of the agent to adapt.
            suggested_changes (Dict[str, Any]): Suggested parameter changes.
            
        Returns:
            bool: True if changes were applied, False if escalation is needed.
        """
        current_config = self.ucs_runtime.agent_configs.get(agent_name, {})
        new_config = current_config.copy()
        
        # Check if any changes are outside acceptable ranges
        for param, value in suggested_changes.items():
            if not self.is_within_range(agent_name, param, value):
                # Escalate for approval if outside range
                return await self.request_approval(agent_name, {param: value})
        
        # Apply changes within acceptable ranges
        for param, value in suggested_changes.items():
            # Navigate nested dictionaries to set the parameter
            param_parts = param.split(".")
            target = new_config
            for part in param_parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[param_parts[-1]] = value
        
        # Update agent configuration
        self.ucs_runtime.agent_configs[agent_name] = new_config
        logger.info(f"Adapted parameters for {agent_name}: {suggested_changes}")
        return True

    async def request_approval(self, agent_name: str, changes: Dict[str, Any]) -> bool:
        """Request human approval for significant parameter changes.
        
        Args:
            agent_name (str): Name of the agent.
            changes (Dict[str, Any]): Parameter changes requiring approval.
            
        Returns:
            bool: True if approved, False otherwise.
        """
        # In a real implementation, this would integrate with a chat interface
        # or external approval system. For now, we'll log the request.
        logger.warning(f"Approval requested for {agent_name} changes: {changes}")
        # For this implementation, we'll return False to indicate escalation
        return False

    async def orchestrate_agent(self, agent_name: str, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Orchestrate an agent execution with LLM evaluation.
        
        Args:
            agent_name (str): Name of the agent to execute.
            method_name (str): Name of the method to execute.
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.
            
        Returns:
            Dict[str, Any]: The result of the orchestration.
        """
        try:
            # Run the agent method
            result = self.ucs_runtime.run_agent(agent_name, method_name, *args, **kwargs)
            
            # Evaluate the result with LLM
            evaluation = await self.evaluate_agent_output(agent_name, result)
            
            # Process the evaluation decision
            decision = evaluation.get("decision", "failure")
            if decision == "adjust":
                # Extract suggested changes from evaluation
                changes = evaluation.get("suggested_changes", {})
                await self.adapt_parameters(agent_name, changes)
            elif decision == "escalate":
                await self.request_approval(agent_name, {})
                
            return {
                "agent": agent_name,
                "method": method_name,
                "result": result,
                "evaluation": evaluation
            }
        except Exception as e:
            logger.error(f"Error orchestrating agent {agent_name}: {e}")
            return {
                "agent": agent_name,
                "method": method_name,
                "error": str(e)
            }

    async def process_user_request(self, user_input: str, conversation_history: List[Dict[str, str]]) -> dict:
        """Process user request using LLM to determine appropriate agents.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        # Initialize tool call tracking
        tool_calls = []
        
        # Construct prompt for LLM with agent information
        # The agent information is now automatically included by the ContextualLLMService
        # These prompts are more prescriptive because I'm using an 8B model.  The model is
        # too small to show emergent properties like automatically testing for DNS entries
        # when the initial URL check fails.
        # TODO: Need to test with bigger models to see where emergence happens reliably.
        prompt = f"User request: {user_input}\n"
        prompt += "\nINSTRUCTIONS:\n"
        prompt += "1. First, determine if any tools need to be called to fulfill the user's request.\n"
        prompt += "2. You may make up to TWO tool calls to investigate an issue thoroughly.\n"
        prompt += "3. After investigating, provide a clear explanation to the user about what you found and what it means.\n"
        prompt += "4. Do NOT make endless recursive calls - limit yourself to the tools needed to answer the user's question.\n"
        prompt += "\nTo make a tool call, respond with a JSON object in the following EXACT format:\n"
        prompt += "{\n"
        prompt += '  "tool_call": {\n'
        prompt += '    "agent_name": "SampleAgentB",\n'
        prompt += '    "method_name": "perform_website_check",\n'
        prompt += '    "parameters": {"url": "https://example.com"}\n'
        prompt += "  }\n"
        prompt += "}\n"
        prompt += "IMPORTANT: Use EXACTLY 'agent_name', 'method_name', and 'parameters' as the keys.\n"
        prompt += "IMPORTANT: Respond ONLY with the JSON object if requesting agent execution. "
        prompt += "Do not include any other text, markdown, or formatting.\n"
        prompt += "If responding directly to the user, provide a helpful response in plain text.\n"
        prompt += "Only use the agent names and method names that are available.\n"
        prompt += "Special Instructions:\n"
        prompt += "- Use the ConfigManager agent for requests related to listing configurations, loading configurations, or listing loaded agents\n"
        
        # Add domain-specific context if available
        additional_info = getattr(self.ucs_runtime, 'additional_prompt_info', {})
        if additional_info:
            domain_context = additional_info.get("domain_context", "")
            if domain_context:
                prompt = f"[DOMAIN CONTEXT: {domain_context}]\n\n{prompt}"
        
        try:
            # Track tool calls to prevent infinite loops
            tool_calls_made = []
            max_tool_calls = 2  # Limit to two tool calls for focused investigation
            
            while len(tool_calls_made) < max_tool_calls:
                # Get LLM response using contextual service (agent registry is now embedded)
                llm_response = await self.llm_service.generate_response(prompt)
                
                # Try to parse as JSON for tool call
                try:
                    response_json = self._parse_llm_json_response(llm_response)
                    # Handle case where _parse_llm_json_response returns an error object
                    if "error" in response_json:
                        # Return original response as direct response to user with tool call info
                        return {
                            "response": llm_response,
                            "tool_calls": tool_calls
                        }
                        
                    if "tool_call" in response_json:
                        # Check if this is a duplicate tool call
                        tool_call = response_json["tool_call"]
                        tool_call_key = (tool_call["agent_name"], tool_call["method_name"], 
                                       tuple(sorted(tool_call.get("parameters", {}).items())))
                        
                        if tool_call_key in tool_calls_made:
                            # Prevent infinite loops by breaking if we've made this exact call before
                            break
                            
                        tool_calls_made.append(tool_call_key)
                        
                        # Execute the requested agent method
                        agent_name = tool_call["agent_name"]
                        method_name = tool_call["method_name"]
                        parameters = tool_call.get("parameters", {})
                        
                        # Record the tool call
                        tool_call_info = {
                            "agent_name": agent_name,
                            "method_name": method_name,
                            "parameters": parameters
                        }
                        
                        # Execute agent method
                        try:
                            result = self.ucs_runtime.run_agent(agent_name, method_name, **parameters)
                            
                            # Record the tool response
                            tool_call_info["result"] = result
                            tool_call_info["success"] = True
                            tool_calls.append(tool_call_info)
                            
                            # Generate follow-up prompt with the result
                            prompt = f"Previous tool call result:\n"
                            prompt += f"Agent: {agent_name}\n"
                            prompt += f"Method: {method_name}\n"
                            prompt += f"Parameters: {parameters}\n"
                            prompt += f"Result: {json.dumps(result)}\n\n"
                            prompt += "INSTRUCTIONS:\n"
                            prompt += "1. Analyze the result above.\n"
                            prompt += "2. You may make ONE more tool call if needed to complete your investigation.\n"
                            prompt += "3. For website errors, perform a DNS lookup using SampleAgentA to determine if the domain exists.\n"
                            prompt += "4. After investigating, provide a clear explanation to the user about what you found and what it means.\n"
                            prompt += "5. Do NOT make endless recursive calls - limit yourself to the tools needed to answer the user's question.\n"
                            prompt += "To make a tool call, use the EXACT same JSON format as before:\n"
                            prompt += "{\n"
                            prompt += '  "tool_call": {\n'
                            prompt += '    "agent_name": "SampleAgentA",\n'
                            prompt += '    "method_name": "perform_dns_lookup",\n'
                            prompt += '    "parameters": {"domain": "example.com"}\n'
                            prompt += "  }\n"
                            prompt += "}\n"
                            prompt += "IMPORTANT: Use EXACTLY 'agent_name', 'method_name', and 'parameters' as the keys.\n"
                            prompt += "Only use the agent names and method names that are available.\n"
                            
                            # If this was an error result, encourage follow-up investigation
                            if isinstance(result, dict) and result.get("status") == "error":
                                prompt += "IMPORTANT: The previous tool call resulted in an error. "
                                prompt += "Perform one more investigation tool call if it would help clarify the issue.\n"
                                prompt += "For website errors, a DNS lookup using SampleAgentA can determine if the domain exists.\n"
                                prompt += "When analyzing the results, remember that errors indicate the website or domain is NOT accessible.\n"
                                
                        except Exception as e:
                            # Handle agent execution errors
                            tool_call_info["result"] = {"error": str(e)}
                            tool_call_info["success"] = False
                            tool_calls.append(tool_call_info)
                            
                            prompt = f"Error executing tool call:\n"
                            prompt += f"Agent: {agent_name}\n"
                            prompt += f"Method: {method_name}\n"
                            prompt += f"Parameters: {parameters}\n"
                            prompt += f"Error: {str(e)}\n\n"
                            prompt += "INSTRUCTIONS:\n"
                            prompt += "1. Analyze the error above.\n"
                            prompt += "2. You may make ONE more tool call if needed to complete your investigation.\n"
                            prompt += "3. For website errors, perform a DNS lookup using SampleAgentA to determine if the domain exists.\n"
                            prompt += "4. After investigating, provide a clear explanation to the user about what you found and what it means.\n"
                            prompt += "5. Do NOT make endless recursive calls - limit yourself to the tools needed to answer the user's question.\n"
                            prompt += "IMPORTANT: Errors indicate that the website or domain is NOT accessible. Make sure to communicate this clearly to the user.\n"
                            prompt += "To make a tool call, use the EXACT same JSON format as before:\n"
                            prompt += "{\n"
                            prompt += '  "tool_call": {\n'
                            prompt += '    "agent_name": "SampleAgentA",\n'
                            prompt += '    "method_name": "perform_dns_lookup",\n'
                            prompt += '    "parameters": {"domain": "example.com"}\n'
                            prompt += "  }\n"
                            prompt += "}\n"
                            prompt += "IMPORTANT: Use EXACTLY 'agent_name', 'method_name', and 'parameters' as the keys.\n"
                            prompt += "Only use the agent names and method names that are available.\n"
                            
                        # Continue the loop to get the next LLM response
                        continue
                        
                except (json.JSONDecodeError, Exception):
                    # Not a JSON response or parsing error, try to parse with our helper
                    response_json = self._parse_llm_json_response(llm_response)
                    # If parsing failed, return as direct response to user
                    if "error" in response_json:
                        return {
                            "response": llm_response,
                            "tool_calls": tool_calls
                        }
                        
            # If we've reached the maximum number of tool calls, we need to generate a final response
            # Check if we have any errors that we can directly interpret
            error_response = self._generate_error_response(tool_calls, user_input)
            if not error_response.startswith("I encountered an error while checking the website"):
                # We have a specific error response, use it
                return {
                    "response": error_response,
                    "tool_calls": tool_calls
                }
            
            # Generate a final prompt to get a user-friendly response
            final_prompt = f"User request: {user_input}\n"
            final_prompt += "INSTRUCTIONS:\n"
            final_prompt += "Provide a clear, user-friendly response to the original user request based on all the tool call results above.\n"
            final_prompt += "Explain what was found and what it means in plain language.\n"
            
            # Add domain-specific instructions if available
            additional_info = getattr(self.ucs_runtime, 'additional_prompt_info', {})
            if additional_info:
                domain_context = additional_info.get("domain_context", "")
                if domain_context:
                    final_prompt += f"DOMAIN CONTEXT: {domain_context}\n"
                
                instructions = additional_info.get("instructions", [])
                if instructions:
                    final_prompt += "DOMAIN-SPECIFIC INSTRUCTIONS:\n"
                    for i, instruction in enumerate(instructions, 1):
                        final_prompt += f"{i}. {instruction}\n"
                
                error_handling = additional_info.get("error_handling", "")
                if error_handling:
                    final_prompt += f"ERROR HANDLING GUIDANCE: {error_handling}\n"
            
            final_prompt += "ADDITIONAL INSTRUCTIONS:\n"
            final_prompt += "After providing your response, please suggest any additional agents that would be helpful to better troubleshoot or investigate this issue.\n"
            final_prompt += "Format your response like this:\n"
            final_prompt += "Your response here.\n\n"
            final_prompt += "Suggested Agents:\n"
            final_prompt += "- Agent Name: Description of what this agent would do\n"
            final_prompt += "- Another Agent Name: Description of what this agent would do\n"
            final_prompt += "If you don't have any suggestions for additional agents, just provide your response without the 'Suggested Agents' section.\n"
            final_prompt += "Do NOT make any more tool calls.\n"
            final_prompt += "Do NOT include JSON or technical formatting.\n"
            final_prompt += "Just provide a helpful response to the user.\n"
            
            final_response = await self.llm_service.generate_response(final_prompt)
            
            # Extract suggested agents from the response
            suggested_agents = self._extract_suggested_agents(final_response)
            
            # Try to parse the response as JSON to see if it contains suggested agents
            try:
                response_json = self._parse_llm_json_response(final_response)
                if isinstance(response_json, dict) and "response" in response_json:
                    # The LLM provided a structured response with suggested agents
                    return {
                        "response": response_json["response"],
                        "tool_calls": tool_calls,
                        "suggested_agents": response_json.get("suggested_agents", suggested_agents)
                    }
            except:
                # If parsing fails, treat it as a regular response
                pass
            
            # Return the response with any extracted suggested agents
            return {
                "response": final_response,
                "tool_calls": tool_calls,
                "suggested_agents": suggested_agents
            }
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            return {
                "response": "I encountered an error while processing your request. Please try again later.",
                "tool_calls": tool_calls
            }

    def _generate_error_response(self, tool_calls: List[Dict[str, Any]], user_input: str) -> str:
        """Generate a correct response when we know the domain doesn't exist or the website is inaccessible.
        
        Args:
            tool_calls (List[Dict[str, Any]]): The tool calls that were made.
            user_input (str): The original user input.
            
        Returns:
            str: A correct response based on the tool call results.
        """
        # Check if we have any tool calls with errors
        for tool_call in tool_calls:
            result = tool_call.get("result", {})
            if isinstance(result, dict) and result.get("status") == "error":
                # Check for specific error types
                if "Domain does not exist" in result.get("message", ""):
                    return "The domain does not exist. The website you're trying to check is not accessible because the domain name cannot be found."
                elif result.get("error_type") == "DNS_ERROR":
                    return "The website is not accessible. The domain name could not be resolved, which means the website does not exist or is not properly configured."
        
        # If we have both a website check and DNS lookup, and both failed, the website is definitely not accessible
        website_check_failed = False
        dns_lookup_failed = False
        
        for tool_call in tool_calls:
            result = tool_call.get("result", {})
            if isinstance(result, dict) and result.get("status") == "error":
                if tool_call.get("agent_name") == "SampleAgentB" and tool_call.get("method_name") == "perform_website_check":
                    website_check_failed = True
                elif tool_call.get("agent_name") == "SampleAgentA" and tool_call.get("method_name") == "perform_dns_lookup":
                    dns_lookup_failed = True
        
        if website_check_failed and dns_lookup_failed:
            return "The website is not accessible. Both the website check and DNS lookup failed, which indicates that the domain does not exist or is not properly configured."
        
        # If we couldn't determine a specific error, return a generic error message
        return "I encountered an error while checking the website. Please try again later."

    def _extract_suggested_agents(self, response_text: str) -> List[Dict[str, Any]]:
        """Extract suggested agents from the LLM's response text.
        
        Args:
            response_text (str): The LLM's response text.
            
        Returns:
            List[Dict[str, Any]]: A list of suggested agents.
        """
        import re
        
        suggested_agents = []
        
        # Look for the "Suggested Agents:" section
        suggested_agents_section = re.search(r"[Ss]uggested\s+[Aa]gents?:\s*(.*?)(?=\n\n|\Z)", response_text, re.DOTALL)
        if suggested_agents_section:
            agents_text = suggested_agents_section.group(1)
            # Look for agent names and descriptions
            # Match patterns like "- Agent Name: Description" or "* Agent Name: Description"
            agent_matches = re.findall(r"[-*]\s*(.*?):\s*(.*?)(?=\n[-*]|\n\n|\Z)", agents_text, re.DOTALL)
            for agent_name, agent_description in agent_matches:
                # Clean up the agent name and description
                agent_name = agent_name.strip().rstrip(':')
                agent_description = agent_description.strip()
                
                suggested_agents.append({
                    "name": agent_name,
                    "description": agent_description,
                    "capabilities": []
                })
        
        return suggested_agents

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