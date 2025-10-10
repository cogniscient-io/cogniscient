"""Generic Control System (GCS) Runtime for PoC.
Following the ringed architecture refactoring, this is now the kernel layer
that manages services and coordinates system operations.
"""

from cogniscient.engine.kernel import Kernel
from cogniscient.engine.services.config_service import ConfigServiceImpl
from cogniscient.engine.services.agent_service import AgentServiceImpl
from cogniscient.engine.services.llm_kernel_service import LLMServiceImpl
from cogniscient.engine.services.auth_service import AuthServiceImpl
from cogniscient.engine.services.storage_service import StorageServiceImpl
from cogniscient.engine.services.system_parameters_service import SystemParametersService
from cogniscient.engine.services.mcp_service import MCPService
from cogniscient.engine.services.llm_kernel_service import LLMServiceImpl
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings


class GCSRuntime:
    """Core GCS runtime refactored to follow ringed architecture as the kernel."""

    def __init__(self, config_dir: str = ".", agents_dir: str = "cogniscient/agentSDK"):
        """Initialize the GCS runtime following the ringed architecture.
        
        Args:
            config_dir (str): Directory to load agent configurations from.
            agents_dir (str): Directory where agent modules are located.
        """
        # Initialize the kernel
        self.kernel = Kernel()
        
        # Initialize system services in dependency order
        self.config_service = ConfigServiceImpl(config_dir=config_dir)
        self.system_parameters_service = SystemParametersService()
        self.agent_service = AgentServiceImpl(
            agents_dir=agents_dir,
            runtime_ref=self
        )
        
        # Initialize attributes needed by session manager
        self.agents = {}
        self.chat_interfaces = []
        self.current_config_name = "default"
        
        # Initialize token manager for OAuth
        self.token_manager = TokenManager(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        # Initialize the LLM provider service with token manager
        from cogniscient.llm.llm_provider_service import LLMService
        llm_service = LLMService(self.token_manager)
        llm_service.set_provider(settings.default_provider)
        
        # Initialize the LLM control service that handles orchestration, retry logic, and error handling
        from cogniscient.engine.services.llm_control_service import LLMControlService
        self.llm_control_service = LLMControlService(llm_service)  # Using new LLMService class
        
        # Initialize the prompt construction service that handles contextual formatting
        from cogniscient.engine.services.prompt_construction_service import PromptConstructionService
        self.prompt_construction_service = PromptConstructionService(
            agent_registry=None,
            system_services={},
            mcp_client_service=None
        )
        
        # Initialize MCP service
        self.mcp_service = None
        
        # Initialize the contextual LLM service with the LLM service (not the control service)
        # The control service handles the orchestration outside of the contextual service
        from cogniscient.engine.llm_orchestrator.contextual_llm_service import ContextualLLMService
        self.llm_service = ContextualLLMService(
            provider_manager=llm_service,  # Use LLM service, not control service
            prompt_construction_service=self.prompt_construction_service
        )
        
        # Initialize auth and storage services
        self.auth_service = AuthServiceImpl(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        self.storage_service = StorageServiceImpl()
        
        # Register services with the kernel
        self.kernel.register_service("config", self.config_service)
        self.kernel.register_service("agent", self.agent_service)
        self.kernel.register_service("llm", LLMServiceImpl(
            provider_manager=llm_service,
            mcp_client_service=None  # Will be updated after MCP initialization
        ))
        self.kernel.register_service("llm_control", self.llm_control_service)  # Register the control service
        self.kernel.register_service("auth", self.auth_service)
        self.kernel.register_service("storage", self.storage_service)
        self.kernel.register_service("system_params", self.system_parameters_service)
        
        # Initialize the MCP service after all other components
        # This prevents initialization order issues
        self.mcp_service = MCPService(self)
        
        # Update the LLM service with MCP client service now that it's available
        if hasattr(self.llm_service, 'prompt_construction_service') and self.llm_service.prompt_construction_service:
            self.llm_service.prompt_construction_service.mcp_client_service = self.mcp_service.mcp_client
        elif hasattr(self.llm_service, 'mcp_client_service'):
            self.llm_service.mcp_client_service = self.mcp_service.mcp_client
        
        # Also update the prompt construction service if it exists
        if hasattr(self, 'prompt_construction_service'):
            self.prompt_construction_service.mcp_client_service = self.mcp_service.mcp_client
        
        # Also update the LLM service in the kernel
        llm_service_impl_kernel = LLMServiceImpl(
            provider_manager=llm_service,  # Use the new LLMService class
            mcp_client_service=self.mcp_service.mcp_client
        )
        llm_service_impl_kernel.set_runtime(self)  # Set runtime for the kernel's LLM service instance
        self.kernel.service_registry["llm"] = llm_service_impl_kernel
        
        # Set runtime reference in services that need access to MCP
        self.config_service.set_runtime(self)
        self.system_parameters_service.set_runtime(self)
        self.agent_service.set_runtime(self)
        self.storage_service.set_runtime(self)
        self.auth_service.set_runtime(self)
        # Note: self.llm_service is ContextualLLMService which doesn't have set_runtime method
        # The LLMServiceImpl instance in kernel registry has runtime set separately
        
        # Set the LLM control service in the kernel
        self.kernel.set_llm_control_service(self.llm_control_service)
        
        # Register MCP tools for services that have them - now that MCP service is initialized
        self.config_service.register_mcp_tools()
        self.system_parameters_service.register_mcp_tools()
        self.agent_service.register_mcp_tools()
        self.storage_service.register_mcp_tools()
        # Use the LLM service from the kernel's service registry
        llm_service_impl = self.kernel.service_registry.get("llm")
        if llm_service_impl and hasattr(llm_service_impl, "register_mcp_tools"):
            llm_service_impl.register_mcp_tools()
        self.auth_service.register_mcp_tools()
    
    def register_chat_interface(self, chat_interface):
        """Register a chat interface with the runtime."""
        # Register with the kernel instead of the runtime
        self.chat_interfaces.append(chat_interface)
        # Also register the chat interface with the kernel for central management
        if hasattr(self.kernel, 'set_chat_interface'):
            self.kernel.set_chat_interface(chat_interface)
    
    def unregister_chat_interface(self, chat_interface):
        """Unregister a chat interface from the runtime."""
        if chat_interface in self.chat_interfaces:
            self.chat_interfaces.remove(chat_interface)
    
    def get_current_config_name(self):
        """Get the name of the current configuration."""
        return self.current_config_name

    async def load_all_agents(self, config: dict = None) -> bool:
        """Load all available agents."""
        return await self.agent_service.load_all_agents(config)

    def set_llm_orchestrator(self, orchestrator):
        """Set the LLM orchestrator in the kernel."""
        if hasattr(self.kernel, 'set_llm_orchestrator'):
            self.kernel.set_llm_orchestrator(orchestrator)
            
        # Also register orchestrator in the runtime for backward compatibility
        self.llm_orchestrator = orchestrator




























    def start_kernel_loop(self):
        """
        Start the kernel's main control loop which manages system operations.
        This is the 'brain' of the system that coordinates all agent activities.
        """
        return self.kernel.start_system()

    async def shutdown(self) -> None:
        """Shutdown all services."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Shutdown MCP services first to properly close connections before other services shut down
        if hasattr(self, 'mcp_service') and self.mcp_service:
            try:
                # Use the new unified shutdown method in MCPService
                await self.mcp_service.shutdown()
                logger.info("MCP service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during MCP service shutdown: {e}")
        
        # Shutdown services through the kernel
        await self.kernel.shutdown()
        
        # Shutdown the LLM control service first
        if hasattr(self, 'llm_control_service') and self.llm_control_service and hasattr(self.llm_control_service, 'shutdown'):
            try:
                await self.llm_control_service.shutdown()
                logger.info("LLM control service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during LLM control service cleanup: {e}")
        
        # Shutdown the prompt construction service if it exists
        if hasattr(self, 'prompt_construction_service') and hasattr(self.prompt_construction_service, 'close'):
            try:
                # Prompt construction service uses sync close method
                self.prompt_construction_service.close()
                logger.info("Prompt construction service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during prompt construction service cleanup: {e}")
        
        # Shutdown the contextual LLM service
        if hasattr(self, 'llm_service') and self.llm_service and hasattr(self.llm_service, 'close'):
            try:
                await self.llm_service.close()
                logger.info("Contextual LLM service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during contextual LLM service cleanup: {e}")
        
        # Also ensure the LLM service instance in the kernel's service registry is closed
        kernel_llm_service = self.kernel.get_service("llm")
        if kernel_llm_service and hasattr(kernel_llm_service, 'provider_manager') and hasattr(kernel_llm_service.provider_manager, 'close'):
            try:
                await kernel_llm_service.provider_manager.close()
                logger.info("Kernel LLM service provider manager shutdown completed")
            except Exception as e:
                logger.warning(f"Error during kernel LLM service provider manager cleanup: {e}")
        
        # Stop the kernel's control loop and thread
        try:
            if hasattr(self.kernel, 'stop_system'):
                self.kernel.stop_system()
                logger.info("Kernel system stopped")
        except Exception as e:
            logger.warning(f"Error during kernel system stop: {e}")
        
        # Additional cleanup for any remaining async resources
        try:
            import gc
            import asyncio
            # Small delay to allow any remaining async operations to complete
            await asyncio.sleep(0.05)
            
            # Force garbage collection to clean up any remaining resources
            gc.collect()
        except Exception as e:
            logger.warning(f"Error during final cleanup: {e}")
        
        # Final cleanup for any remaining aiohttp ClientSession objects
        try:
            # Get all tasks and check for any remaining aiohttp-related tasks
            pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            for task in pending_tasks:
                try:
                    # Cancel any pending tasks related to aiohttp
                    if hasattr(task, '_coro'):
                        coro_name = getattr(task._coro, '__name__', str(task._coro))
                        if 'aiohttp' in coro_name.lower() or 'client' in coro_name.lower():
                            task.cancel()
                except:
                    pass
        except:
            pass
        
        # Additional comprehensive cleanup for aiohttp resources
        try:
            import gc
            import asyncio
            import aiohttp
            
            # Force garbage collection to ensure objects are properly collected
            gc.collect()
            
            # Look for any remaining aiohttp ClientSession and BaseConnector objects
            # and try to close them
            for obj in gc.get_objects():
                try:
                    obj_type = type(obj)
                    module_name = getattr(obj_type, '__module__', '')
                    class_name = obj_type.__name__
                    
                    # Look for aiohttp ClientSession objects
                    if 'aiohttp' in module_name and 'ClientSession' in class_name:
                        if hasattr(obj, '_connector') and obj._connector and hasattr(obj._connector, 'close'):
                            try:
                                if asyncio.iscoroutinefunction(obj._connector.close):
                                    # If we're in an event loop, await the close
                                    try:
                                        loop = asyncio.get_running_loop()
                                        if loop.is_running():
                                            loop.create_task(obj._connector.close())
                                    except RuntimeError:
                                        # No event loop, try to close directly
                                        await obj._connector.close()
                                else:
                                    # Synchronous close method
                                    obj._connector.close()
                            except:
                                pass
                        if hasattr(obj, 'close'):
                            try:
                                if asyncio.iscoroutinefunction(obj.close):
                                    # If we're in an event loop, await the close
                                    try:
                                        loop = asyncio.get_running_loop()
                                        if loop.is_running():
                                            loop.create_task(obj.close())
                                    except RuntimeError:
                                        # No event loop, try to close directly
                                        await obj.close()
                                else:
                                    # Synchronous close method
                                    obj.close()
                            except:
                                pass
                except Exception:
                    pass  # Continue to next object even if this one fails
            
            # More aggressive cleanup: close any lingering connectors
            for obj in gc.get_objects():
                try:
                    obj_type = type(obj)
                    module_name = getattr(obj_type, '__module__', '')
                    class_name = obj_type.__name__
                    
                    # Look for aiohttp BaseConnector objects
                    if 'aiohttp' in module_name and 'Connector' in class_name:
                        if hasattr(obj, 'close'):
                            try:
                                if asyncio.iscoroutinefunction(obj.close):
                                    # If we're in an event loop, await the close
                                    try:
                                        loop = asyncio.get_running_loop()
                                        if loop.is_running():
                                            loop.create_task(obj.close())
                                    except RuntimeError:
                                        # No event loop, try to close directly
                                        await obj.close()
                                else:
                                    # Synchronous close method
                                    obj.close()
                            except:
                                pass
                except Exception:
                    pass  # Continue to next object even if this one fails
        
        except ImportError:
            # aiohttp might not be available in some contexts
            pass
        except Exception:
            # If anything goes wrong in this aggressive cleanup, continue with shutdown
            pass
        
        # Final small delay to allow any cleanup tasks to complete before process termination
        try:
            await asyncio.sleep(0.01)
        except:
            pass
        
        # Final cleanup - ensure logging system is properly shutdown to prevent
        # 'AttributeError: 'NoneType' object has no attribute 'from_exception'' errors
        try:
            import logging
            # Attempt to properly shutdown the logging system
            logging.shutdown()
        except:
            pass  # If logging shutdown fails, continue with process termination
        
        # Additional comprehensive fix: Install a global hook to suppress
        # the specific aiohttp warnings that occur during garbage collection
        import sys
        import warnings
        
        # Temporarily patch sys.excepthook to suppress the specific exceptions during shutdown
        original_excepthook = sys.excepthook
        
        def silent_excepthook(exc_type, exc_value, exc_traceback):
            # Check if this is the specific error we're trying to suppress
            if (exc_type.__name__ == 'AttributeError' and 
                "'NoneType' object has no attribute 'from_exception'" in str(exc_value)):
                return  # Suppress this exception
            # For other exceptions, use the original hook
            original_excepthook(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = silent_excepthook

        # Also temporarily patch warnings.showwarning to suppress specific messages
        original_showwarning = warnings.showwarning
        
        def custom_showwarning(message, category, filename, lineno, file=None, line=None):
            # Check if this is the specific aiohttp warning we want to suppress
            msg_str = str(message)
            if ("ResourceWarning" in msg_str or 
                "ClientSession.__del__" in msg_str or 
                "BaseConnector.__del__" in msg_str or
                ("aiohttp" in msg_str and "AttributeError" in msg_str and "from_exception" in msg_str)):
                return  # Suppress this warning
            # Call the original function for other warnings
            original_showwarning(message, category, filename, lineno, file, line)
        
        warnings.showwarning = custom_showwarning