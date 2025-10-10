"""
High-level LLM service that adds domain context and agent registry information.
"""

import logging
from typing import Dict, Any, Optional
from cogniscient.llm.llm_service import LLMService  # This is the new main LLM service (formerly ProviderManager)


logger = logging.getLogger(__name__)


class ContextualLLMService:
    def __init__(self, provider_manager: 'LLMService' = None, agent_registry: Optional[Dict[str, Any]] = None, system_services: Optional[Dict[str, Any]] = None, mcp_client_service: Optional['MCPClientService'] = None):
        """Initialize the contextual LLM service.
        
        Args:
            provider_manager (LLMService, optional): The LLM service for handling LLM calls (formerly ProviderManager).
            agent_registry (Dict[str, Any], optional): Agent registry information.
            system_services (Dict[str, Any], optional): System services information.
            mcp_client_service (MCPClientService, optional): MCP client service for external agent connections.
        """
        self.provider_manager = provider_manager
        self.agent_registry = agent_registry
        self.system_services = system_services or {}
        self.mcp_client_service = mcp_client_service  # NEW: MCP client service for external agent connections

    async def generate_response(
        self, 
        prompt: str, 
        domain: Optional[str] = None, 
        agent_registry: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        include_agent_capabilities: bool = True,
        return_token_counts: bool = False,  # New parameter to return token counts
        stream: bool = False,  # Add stream parameter
        **kwargs
    ) -> str | Dict[str, Any]:
        """Generate a response from the LLM API with contextual information.
        
        Args:
            prompt (str): The user's prompt.
            domain (str, optional): Domain context to add to the system message.
            agent_registry (Dict[str, Any], optional): Agent registry information.
            model (str, optional): The model to use.
            temperature (float): Temperature for generation (0.0 to 1.0).
            max_tokens (int, optional): Maximum number of tokens to generate.
            include_agent_capabilities (bool): Whether to include agent capabilities in the prompt.
            return_token_counts (bool): Whether to return token count information.
            **kwargs: Additional arguments to pass to the LLM API.
            
        Returns:
            Union[str, Dict[str, Any]]: The generated response content or a dict with response and token counts.
        """
        if not self.provider_manager:
            # Return a mock response if no provider manager is configured
            domain_context = f" [Domain: {domain}]" if domain else ""
            response = f"Mock response to: {prompt}{domain_context}"
            
            # Return mock response with token counts if requested
            if return_token_counts:
                # For mock response, we'll count tokens using LiteLLM
                import litellm
                mock_tokens = litellm.token_counter(model=model or "gpt-3.5-turbo", text=response)
                return {
                    "response": response,
                    "token_counts": {
                        "input_tokens": 0,  # No input tokens for a mock response
                        "output_tokens": mock_tokens,
                        "total_tokens": mock_tokens
                    }
                }
            
            return response
        
        try:
            # The provider manager should always be available - this is now a requirement
            if not self.provider_manager:
                raise ValueError("ProviderManager not available - this is required for LLM operations")
            
            # Create messages with domain context if available
            messages = []
            system_content = ""
            
            if domain:
                system_content += (f"You are an expert in the {domain} domain. Please explain the error "
                                   f"with information specific to this domain and provide options to resolve it.")

            # Use provided agent_registry or fall back to instance agent_registry
            registry_to_use = agent_registry or self.agent_registry
            
            # Include agent capabilities if requested and available
            if include_agent_capabilities and registry_to_use:
                agent_capabilities = self._format_agent_capabilities(registry_to_use)
                if agent_capabilities:
                    system_content += agent_capabilities
                    
            # Include system service capabilities (always available)
            system_service_capabilities = self._format_system_service_capabilities()
            if system_service_capabilities:
                system_content += system_service_capabilities
                
            if system_content:
                messages.append({"role": "system", "content": system_content})
                
            messages.append({"role": "user", "content": prompt})
            
            # Use the provider manager to generate response
            result = await self.provider_manager.generate_response(
                messages=messages,
                model=model,  # Pass the provided model directly (will use provider defaults if None)
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,  # Pass the stream parameter through
                **kwargs
            )
            
            # Handle the result based on whether it contains token counts or is a streaming generator
            if isinstance(result, dict) and "token_counts" in result and "response" in result:
                # The provider already returned token counts, so use them
                if return_token_counts:
                    return result  # Return as-is with token counts
                else:
                    # Caller doesn't want return_token_counts format, just return response
                    return result["response"]
            else:
                # Check if it's an async generator (streaming case)
                if hasattr(result, '__aiter__'):  # Check if it's an async generator
                    return result  # Return the async generator as-is
                # The provider returned a string or a non-token-count-aware result
                elif return_token_counts:
                    # Return in token count format with zeros for token counts
                    return {
                        "response": result,
                        "token_counts": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0
                        }
                    }
                else:
                    # Return as-is
                    return result
                    
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            error_response = f"Error: Unable to generate response ({str(e)})"
            
            # For streaming errors, we'd return a different kind of generator
            if stream:
                async def error_generator():
                    yield {
                        "content": error_response,
                        "type": "error"
                    }
                    if return_token_counts:
                        yield {
                            "type": "token_counts",
                            "token_counts": {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "total_tokens": 0
                            }
                        }
                
                return error_generator()
            else:
                # Return error response with token counts if requested
                if return_token_counts:
                    import litellm
                    # Use a default model for token counting in case of error
                    default_model = model or "gpt-3.5-turbo"
                    error_tokens = litellm.token_counter(model=default_model, text=error_response)
                    return {
                        "response": error_response,
                        "token_counts": {
                            "input_tokens": 0,  # No input tokens for an error response
                            "output_tokens": error_tokens,
                            "total_tokens": error_tokens
                        }
                    }
                
                return error_response

    def _format_agent_capabilities(self, agent_registry: Dict[str, Any]) -> str:
        """Format agent capabilities for inclusion in system prompt.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
            
        Returns:
            str: Formatted agent capabilities string.
        """
        if not agent_registry:
            return ""
            
        capabilities_str = "\\n[AGENT_REGISTRY]\n"
        for name, agent in agent_registry.items():
            # Try to get agent description
            desc = getattr(agent, "description", f"Agent {name}")
            
            # Try to get agent capabilities/methods if available
            capabilities_str += f"- {name}: {desc}\n"
            
            # If agent has a self_describe method, use it for more detailed info
            if hasattr(agent, "self_describe"):
                try:
                    agent_info = agent.self_describe()
                    methods = agent_info.get("methods", {})
                    if methods:
                        capabilities_str += "  Available methods:\n"
                        for method_name, method_info in methods.items():
                            method_desc = method_info.get("description", "")
                            capabilities_str += f"  - {method_name}: {method_desc}\n"
                            parameters = method_info.get("parameters", {})
                            if parameters:
                                capabilities_str += "    Parameters:\n"
                                for param_name, param_info in parameters.items():
                                    param_type = param_info.get("type", "any")
                                    param_desc = param_info.get("description", "")
                                    required = " (required)" if param_info.get("required", False) else ""
                                    capabilities_str += f"    - {param_name}: {param_type} - {param_desc}{required}\n"
                except Exception:
                    # If self_describe fails, continue with basic info
                    pass
                    
        capabilities_str += "[/AGENT_REGISTRY]\n"
        return capabilities_str

    def set_agent_registry(self, agent_registry: Dict[str, Any], system_services: Optional[Dict[str, Any]] = None, mcp_client_service: Optional['MCPClientService'] = None) -> None:
        """Set the agent registry for this service, with optional system services.
        
        Args:
            agent_registry (Dict[str, Any]): Agent registry information.
            system_services (Dict[str, Any], optional): System services information.
            mcp_client_service (MCPClientService, optional): MCP client service for external agent connections.
        """
        self.agent_registry = agent_registry
        if system_services:
            self.system_services = system_services
        else:
            # Initialize with default system services if not provided
            self.system_services = {}
        
        # Set MCP client service if provided
        if mcp_client_service:
            self.mcp_client_service = mcp_client_service

    def _format_mcp_client_capabilities(self) -> str:
        """Format MCP client service capabilities for inclusion in system prompt.
        
        Returns:
            str: Formatted MCP client service capabilities string.
        """
        # Since MCP functionality is now properly exposed as the MCPClient agent,
        # we don't need to present standalone mcp_* tools in the system capabilities.
        # The LLM can access all MCP functionality through the MCPClient agent methods.
        if not self.mcp_client_service:
            return ""
            
        # Return empty string since MCP functionality is available through the MCPClient agent
        return ""

    def get_all_available_tools(self) -> Dict[str, Any]:
        """Get a comprehensive list of all available tools in the system.
        
        Returns:
            Dict containing all available tools organized by type.
        """
        tools_info = {
            "system_services": {},
            "mcp_tools": {},
            "agent_methods": {},
            "connected_external_agent_tools": {}
        }
        
        # 1. System services - now available via MCP, so we'll keep an empty dict
        # The actual tools are available through the MCP client service
        tools_info["system_services"] = {}
        
        # 2. MCP client tools for LLM control (using internal mcp. namespace, not system. namespace)
        if self.mcp_client_service:
            tools_info["mcp_tools"] = {
                "mcp.connect_external_agent": {
                    "description": "Connect to an external agent using MCP protocol",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True},
                        "connection_params": {"type": "object", "description": "Connection parameters including type, url/command, etc.", "required": True}
                    }
                },
                "mcp.list_connected_agents": {
                    "description": "Get a list of currently connected external agents",
                    "parameters": {}
                },
                "mcp.disconnect_external_agent": {
                    "description": "Disconnect from an external agent by its ID",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent to disconnect", "required": True}
                    }
                },
                "mcp.list_external_agent_capabilities": {
                    "description": "Get capabilities (tools) of a connected external agent",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True}
                    }
                },
                "mcp.call_external_agent_tool": {
                    "description": "Call a specific tool on a connected external agent",
                    "parameters": {
                        "agent_id": {"type": "string", "description": "Unique identifier for the external agent", "required": True},
                        "tool_name": {"type": "string", "description": "Name of the tool to call", "required": True},
                        "tool_parameters": {"type": "object", "description": "Parameters to pass to the tool", "required": False}
                    }
                }
            }
            
            # Also include tools from connected external agents
            connected_tools = self.mcp_client_service.get_registered_external_tools()
            if connected_tools.get("success"):
                tools_info["connected_external_agent_tools"] = connected_tools.get("external_agent_tools", {})
        
        # 3. Agent methods (if agent registry is available)
        if self.agent_registry:
            for agent_name, agent_instance in self.agent_registry.items():
                agent_methods = {}
                if hasattr(agent_instance, "self_describe"):
                    try:
                        agent_info = agent_instance.self_describe()
                        agent_methods = agent_info.get("methods", {})
                    except Exception:
                        # If self_describe fails, try to extract methods using introspection
                        for attr_name in dir(agent_instance):
                            if not attr_name.startswith('_') and callable(getattr(agent_instance, attr_name)):
                                agent_methods[attr_name] = {
                                    "description": f"Method {attr_name} on agent {agent_name}",
                                    "parameters": {}
                                }
                
                if agent_methods:
                    tools_info["agent_methods"][agent_name] = agent_methods
        
        return tools_info

    async def close(self):
        """Close any resources held by the contextual service."""
        if self.provider_manager and hasattr(self.provider_manager, 'close'):
            await self.provider_manager.close()
        
        # Additional cleanup to ensure all async resources are closed
        # especially the LiteLLM async success handler tasks
        try:
            import litellm
            import asyncio
            import gc
            
            # Process any pending logs to prevent the async_success_handler warning
            if hasattr(litellm, 'batch_logging'):
                await litellm.batch_logging()

            # Try to properly close module-level clients
            if hasattr(litellm, 'module_level_aclient'):
                try:
                    close_method = litellm.module_level_aclient.close
                    # Check if the close method is async (coroutine)
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        # If it's not a coroutine, call it directly
                        close_method()
                except Exception:
                    pass  # Ignore errors during close attempt

            if hasattr(litellm, 'module_level_client'):
                try:
                    litellm.module_level_client.close()
                except Exception:
                    pass  # Ignore errors during close attempt

            # Try to properly close cached clients in LLMClientCache
            if hasattr(litellm, 'in_memory_llm_clients_cache'):
                try:
                    # Get the cached clients and close them
                    cache = litellm.in_memory_llm_clients_cache
                    if hasattr(cache, 'cache_dict'):
                        for key, cached_client in list(cache.cache_dict.items()):
                            if hasattr(cached_client, 'aclose'):
                                # Async close method
                                try:
                                    await cached_client.aclose()
                                except Exception:
                                    pass  # Ignore errors during close attempt
                            elif hasattr(cached_client, 'close'):
                                # Check if close method is async (coroutine)
                                close_method = cached_client.close
                                if asyncio.iscoroutinefunction(close_method):
                                    try:
                                        await close_method()
                                    except Exception:
                                        pass  # Ignore errors during close attempt
                                else:
                                    # Sync close method
                                    try:
                                        close_method()
                                    except Exception:
                                        pass  # Ignore errors during close attempt
                        # Clear the cache after closing
                        cache.cache_dict.clear()
                except Exception:
                    pass  # Ignore errors during cache cleanup

            # Try to properly close any async clients
            if hasattr(litellm, 'aclient_session') and litellm.aclient_session:
                try:
                    loop = asyncio.get_running_loop()
                    # If we're in a running loop, schedule the closure
                    task = loop.create_task(litellm.aclient_session.aclose())
                    await task  # Wait for the task to complete
                except RuntimeError:
                    # No event loop running, we can create a new one
                    await litellm.aclient_session.aclose()

            # Additional aiohttp-specific cleanup - try to close any lingering aiohttp resources
            try:
                # Access aiohttp connector connections and close them
                if hasattr(litellm, 'aclient_session') and litellm.aclient_session:
                    if hasattr(litellm.aclient_session, '_connector'):
                        try:
                            await litellm.aclient_session._connector.close()
                        except Exception:
                            pass  # Connector might already be closed
            except Exception:
                pass  # Safe to ignore if these attributes don't exist

            # Clear callback lists to prevent async handlers from running
            if hasattr(litellm, 'success_callback'):
                litellm.success_callback = []
            if hasattr(litellm, 'failure_callback'):
                litellm.failure_callback = []
            if hasattr(litellm, '_async_success_callback'):
                litellm._async_success_callback = []
            if hasattr(litellm, '_async_failure_callback'):
                litellm._async_failure_callback = []

            # Force garbage collection to clean up any remaining resources
            gc.collect()

        except Exception as e:
            # If the above fails, try a different approach
            try:
                import gc
                # Force garbage collection to clean up any remaining resources
                gc.collect()
            except:
                pass  # If all else fails, just continue

    def _format_system_service_capabilities(self) -> str:
        """Format system service capabilities for inclusion in system prompt.
        
        Returns:
            str: Formatted system service capabilities string.
        """
        # With MCP integration, system service capabilities should be discovered dynamically
        # through the MCP client instead of having them statically provided here
        capabilities_str = "\\n[SYSTEM_SERVICES]\\n"
        capabilities_str += "Note: System services are available via MCP (Model Context Protocol).\n"
        capabilities_str += "Use MCP client tools to discover and invoke system service capabilities dynamically:\n"
        capabilities_str += "- config.list_configurations: List all available system configurations\n"
        capabilities_str += "- config.load_configuration: Load a specific system configuration by name\n"
        capabilities_str += "- config.get_configuration: Get a specific system configuration\n"
        capabilities_str += "- config.get_all_cached_configs: Get all cached configurations\n"
        capabilities_str += "- config.clear_config_cache: Clear the configuration cache\n"
        capabilities_str += "- system.get_parameters: Get current system parameter values\n"
        capabilities_str += "- system.set_parameter: Set a system parameter value\n"
        capabilities_str += "- system.get_parameter_descriptions: Get descriptions of all system parameters\n"
                    
        capabilities_str += "[/SYSTEM_SERVICES]\\n"
        
        # Include MCP client capabilities if available
        if self.mcp_client_service:
            capabilities_str += self._format_mcp_client_capabilities()
            
        return capabilities_str