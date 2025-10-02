"""Base module for user request processing functionality in LLM Orchestration Engine."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from cogniscient.engine.services.llm_service import LLMService
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings


logger = logging.getLogger(__name__)


class BaseUserRequestHandler:
    """Base class for processing user requests with shared functionality."""

    def __init__(self, gcs_runtime: GCSRuntime, llm_service: LLMService):
        """Initialize the base request handler.
        
        Args:
            gcs_runtime (GCSRuntime): The GCS runtime instance to manage agents.
            llm_service (LLMService): The LLM service instance.
        """
        self.gcs_runtime = gcs_runtime
        self.llm_service = llm_service

    def _calculate_context_size(self, conversation_history: List[Dict[str, str]]) -> int:
        """Calculate the total context size in characters.
        
        Args:
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            int: Total number of characters in the conversation history.
        """
        total_chars = 0
        for turn in conversation_history:
            total_chars += len(turn.get("content", ""))
        return total_chars

    async def _compress_conversation_history(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Compress the conversation history to reduce context size.
        
        Args:
            conversation_history (List[Dict[str, str]]): The conversation history.
            
        Returns:
            List[Dict[str, str]]: Compressed conversation history.
        """
        if len(conversation_history) < 2:
            return conversation_history
            
        # Use the LLM to summarize the conversation history
        try:
            compression_prompt = "Please summarize the following conversation history in a concise way, preserving the key points and context:\n\n"
            for turn in conversation_history[:-2]:  # Exclude the last two entries
                compression_prompt += f"{turn['role'].title()}: {turn['content']}\n"
            
            compression_prompt += "\nProvide a concise summary that captures the main topics and context of this conversation."
            
            compressed_summary_result = await self.llm_service.generate_response(compression_prompt, return_token_counts=True)
            
            # Handle the response based on whether token counts were returned
            if isinstance(compressed_summary_result, dict) and "token_counts" in compressed_summary_result:
                compressed_summary = compressed_summary_result["response"]
            else:
                compressed_summary = compressed_summary_result
            
            # Replace the conversation history with the summary
            compressed_history = [
                {"role": "system", "content": f"Previous conversation summary: {compressed_summary}"},
                conversation_history[-2],  # Last user input
                conversation_history[-1]   # Last assistant response
            ]
            
            logger.info("Conversation history compressed successfully in orchestrator")
            return compressed_history
        except Exception as e:
            logger.error(f"Failed to compress conversation history in orchestrator: {e}")
            # If compression fails, just return the original history
            return conversation_history

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

    async def _execute_request_logic(
        self, 
        user_input: str, 
        conversation_history: List[Dict[str, str]], 
        send_stream_event: Callable[[str, str, Dict[str, Any]], Any]
    ) -> Dict[str, Any]:
        """Execute the core request processing logic with streaming by default.
        
        Args:
            user_input (str): The user's input message.
            conversation_history (List[Dict[str, str]]): The conversation history.
            send_stream_event (Callable): Function to send streaming events (required)
            
        Returns:
            dict: A dictionary containing the final response and tool call information.
        """
        # Check if this is the synchronous event collector
        import inspect
        is_async_send_stream_event = True
        if not inspect.iscoroutinefunction(send_stream_event):
            # This is a synchronous function, so we'll call it directly without await
            is_async_send_stream_event = False

        # Helper function to call send_stream_event properly
        async def call_send_stream_event(event_type: str, content: str = None, data: Dict[str, Any] = None):
            if send_stream_event:
                if is_async_send_stream_event:
                    await send_stream_event(event_type, content, data)
                else:
                    send_stream_event(event_type, content, data)
            
        # Initialize tool call tracking
        tool_calls = []
        total_token_counts = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        # Check if we should compress based on context window size
        context_size = self._calculate_context_size(conversation_history)
        max_context_size = getattr(self, 'max_context_size', settings.max_context_size)
        
        if context_size > max_context_size:
            # Compress the conversation history
            conversation_history = await self._compress_conversation_history(conversation_history)
        
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
        additional_info = getattr(self.gcs_runtime, 'additional_prompt_info', {})
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
                llm_response_result = await self.llm_service.generate_response(prompt, return_token_counts=True)
                
                # Handle the response based on whether token counts were returned
                if isinstance(llm_response_result, dict) and "token_counts" in llm_response_result:
                    llm_response = llm_response_result["response"]
                    # Add token counts to the total
                    token_counts = llm_response_result["token_counts"]
                    total_token_counts["input_tokens"] += token_counts["input_tokens"]
                    total_token_counts["output_tokens"] += token_counts["output_tokens"]
                    total_token_counts["total_tokens"] += token_counts["total_tokens"]
                else:
                    llm_response = llm_response_result

                # Try to parse as JSON for tool call
                try:
                    response_json = self._parse_llm_json_response(llm_response)
                    # Handle case where _parse_llm_json_response returns an error object
                    if "error" in response_json:
                        # Send a direct response event
                        if send_stream_event:
                            await call_send_stream_event("assistant_response", llm_response, None)
                        return {
                            "response": llm_response,
                            "tool_calls": tool_calls,
                            "token_counts": total_token_counts
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
                        
                        # For streaming, add token counts to tool call info
                        if isinstance(llm_response_result, dict) and "token_counts" in llm_response_result:
                            tool_call_info["token_counts"] = llm_response_result["token_counts"]
                        
                        # Send tool call event to frontend
                        if send_stream_event:
                            await call_send_stream_event("tool_call", None, tool_call_info)
                        
                        # Execute agent method
                        try:
                            result = self.gcs_runtime.run_agent(agent_name, method_name, **parameters)
                            
                            # Record the tool response
                            tool_call_info["result"] = result
                            tool_call_info["success"] = True
                            tool_calls.append(tool_call_info)
                            
                            # Send tool response event to frontend
                            if send_stream_event:
                                await send_stream_event("tool_response", None, tool_call_info)
                            
                            # Generate follow-up prompt with the result
                            prompt = "Previous tool call result:\n"
                            prompt += f"Agent: {agent_name}\n"
                            prompt += f"Method: {method_name}\n"
                            prompt += f"Parameters: {parameters}\n"
                            # Format configuration results more clearly to avoid placeholder issues
                            if agent_name == "ConfigManager" and method_name == "list_configurations":
                                if isinstance(result, dict) and result.get("status") == "success":
                                    configs = result.get("configurations", [])
                                    config_names = [config.get("name", "") for config in configs if isinstance(config, dict)]
                                    prompt += f"Result: Successfully retrieved {len(config_names)} configurations: {', '.join(config_names)}\n\n"
                                else:
                                    prompt += f"Result: {json.dumps(result)}\n\n"
                            else:
                                prompt += f"Result: {json.dumps(result)}\n\n"
                            
                            prompt += "INSTRUCTIONS:\n"
                            prompt += "1. Analyze the result above.\n"
                            prompt += "2. You may make ONE more tool call if needed to complete your investigation.\n"
                            # Only suggest DNS lookup for website-related issues, not for configuration listing
                            if agent_name != "ConfigManager":
                                prompt += "3. For website errors, perform a DNS lookup using SampleAgentA to determine if the domain exists.\n"
                            else:
                                prompt += "3. This is a configuration listing result. Do not perform DNS lookups for configuration data.\n"
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
                            # But only for non-configuration tools
                            if isinstance(result, dict) and result.get("status") == "error" and agent_name != "ConfigManager":
                                prompt += "IMPORTANT: The previous tool call resulted in an error. "
                                prompt += "Perform one more investigation tool call if it would help clarify the issue.\n"
                                prompt += "For website errors, a DNS lookup using SampleAgentA can determine if the domain exists.\n"
                                prompt += "When analyzing the results, remember that errors indicate the website or domain is NOT accessible.\n"
                                
                        except Exception as e:
                            # Handle agent execution errors
                            tool_call_info["result"] = {"error": str(e)}
                            tool_call_info["success"] = False
                            tool_calls.append(tool_call_info)
                            
                            # Send tool response event to frontend
                            if send_stream_event:
                                await send_stream_event("tool_response", None, tool_call_info)
                            
                            prompt = "Error executing tool call:\n"
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
                        if send_stream_event:
                            await send_stream_event("assistant_response", llm_response, None)
                            # Send token counts for streaming
                            await send_stream_event("token_counts", None, total_token_counts)
                        return {
                            "response": llm_response,
                            "tool_calls": tool_calls,
                            "token_counts": total_token_counts
                        }
                    else:
                        # Not an error, but also not a tool call - handle as direct response
                        if send_stream_event:
                            await send_stream_event("assistant_response", llm_response, None)
                            # Send token counts for streaming
                            await send_stream_event("token_counts", None, total_token_counts)
                        return {
                            "response": llm_response,
                            "tool_calls": tool_calls,
                            "token_counts": total_token_counts
                        }
            
            # If we've reached the maximum number of tool calls, we need to generate a final response
            # Check if we have any errors that we can directly interpret
            error_response = self._generate_error_response(tool_calls, user_input)
            if not error_response.startswith("I encountered an error while checking the website"):
                # We have a specific error response, use it
                if send_stream_event:
                    await send_stream_event("assistant_response", error_response, None)
                return {
                    "response": error_response,
                    "tool_calls": tool_calls,
                    "token_counts": total_token_counts
                }
            
            # Generate a final prompt to get a user-friendly response
            final_prompt = f"User request: {user_input}\n"
            final_prompt += "INSTRUCTIONS:\n"
            final_prompt += "Provide a clear, user-friendly response to the original user request based on all the tool call results above.\n"
            final_prompt += "Explain what was found and what it means in plain language.\n"
            
            # Add domain-specific instructions if available
            additional_info = getattr(self.gcs_runtime, 'additional_prompt_info', {})
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
            
            final_response_result = await self.llm_service.generate_response(final_prompt, return_token_counts=True)
            
            # Handle the response based on whether token_counts were returned
            if isinstance(final_response_result, dict) and "token_counts" in final_response_result:
                final_response = final_response_result["response"]
                # Add token_counts to the total
                token_counts = final_response_result["token_counts"]
                total_token_counts["input_tokens"] += token_counts["input_tokens"]
                total_token_counts["output_tokens"] += token_counts["output_tokens"]
                total_token_counts["total_tokens"] += token_counts["total_tokens"]
            else:
                final_response = final_response_result
            
            # Extract suggested agents from the response
            suggested_agents = self._extract_suggested_agents(final_response)
            
            # Try to parse the response as JSON to see if it contains suggested agents
            try:
                response_json = self._parse_llm_json_response(final_response)
                if isinstance(response_json, dict) and "response" in response_json:
                    # The LLM provided a structured response with suggested agents
                    # Send suggested agents event
                    if suggested_agents:
                        if send_stream_event:
                            await send_stream_event("suggested_agents", None, suggested_agents)
                    
                    # Send the final response
                    if send_stream_event:
                        await send_stream_event("assistant_response", response_json["response"], None)
                    
                    # Send token counts separately if available
                    logger.debug(f"Sending final token counts: {total_token_counts}")
                    if send_stream_event:
                        await send_stream_event("token_counts", None, total_token_counts)
                    logger.debug("Sent final token counts event")
                    
                    return self._compose_result(
                        response=response_json["response"],
                        tool_calls=tool_calls,
                        suggested_agents=response_json.get("suggested_agents", suggested_agents),
                        token_counts=total_token_counts
                    )
            except Exception:
                # If parsing fails, treat it as a regular response
                pass
            
            # Send suggested agents if any
            if suggested_agents:
                if send_stream_event:
                    await send_stream_event("suggested_agents", None, suggested_agents)
            
            # Send the final response
            if send_stream_event:
                await send_stream_event("assistant_response", final_response, None)
            
            # Send token counts separately if available
            logger.debug(f"Sending final token counts (second path): {total_token_counts}")
            if send_stream_event:
                await send_stream_event("token_counts", None, total_token_counts)
            logger.debug("Sent final token counts event (second path)")
            
            # Return the response with any extracted suggested agents
            return self._compose_result(
                response=final_response,
                tool_calls=tool_calls,
                suggested_agents=suggested_agents,
                token_counts=total_token_counts
            )
            
        except Exception as e:
            logger.error(f"Error processing user request: {e}")
            if send_stream_event:
                await send_stream_event("assistant_response", "I encountered an error while processing your request. Please try again later.", None)
                # Send token counts even in error case
                await send_stream_event("token_counts", None, total_token_counts)
            return {
                "response": "I encountered an error while processing your request. Please try again later.",
                "tool_calls": tool_calls,
                "token_counts": total_token_counts
            }

    def _compose_result(self, response: str, tool_calls: List[Dict[str, Any]], 
                       suggested_agents: List[Dict[str, Any]] = None, 
                       token_counts: Dict[str, int] = None) -> Dict[str, Any]:
        """Compose the final result dictionary.
        
        Args:
            response: The final response string
            tool_calls: List of tool calls made during processing
            suggested_agents: List of suggested agents
            token_counts: Token usage counts
            
        Returns:
            Dictionary containing all result information
        """
        result = {
            "response": response,
            "tool_calls": tool_calls
        }
        
        if suggested_agents:
            result["suggested_agents"] = suggested_agents
        if token_counts:
            result["token_counts"] = token_counts
            
        return result
