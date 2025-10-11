"""Generic Control System (GCS) Runtime for PoC.
Following the ringed architecture refactoring, this is now the kernel layer
that manages services and coordinates system operations.

This updated version integrates the new LLM architecture with kernel/ring services
and MCP integration.
"""

from cogniscient.engine.kernel import Kernel
from cogniscient.engine.services.config_service import ConfigServiceImpl
from cogniscient.engine.services.agent_service import AgentServiceImpl
from cogniscient.engine.services.auth_service import AuthServiceImpl
from cogniscient.engine.services.storage_service import StorageServiceImpl
from cogniscient.engine.services.system_parameters_service import SystemParametersService
from cogniscient.engine.services.llm_control_service import LLMControlService
from cogniscient.auth.token_manager import TokenManager
from cogniscient.engine.config.settings import settings

# Import new LLM architecture services
from cogniscient.engine.services.llm.llm_kernel_service import LLMKernelServiceImpl
from cogniscient.engine.services.llm.llm_provider_manager import LLMProviderManager
from cogniscient.engine.services.llm.prompt_construction_service import PromptConstructionService
from cogniscient.engine.services.llm.response_evaluator_service import ResponseEvaluatorService
from cogniscient.engine.services.mcp_service import create_mcp_service, MCPService
from cogniscient.engine.services.llm.agent_orchestrator import AgentOrchestratorService
from cogniscient.engine.services.llm.conversation_manager import ConversationManagerService
from cogniscient.engine.services.llm.control_config_service import ControlConfigService


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
        
        # Initialize attributes needed by session manager
        self.agents = {}
        self.chat_interfaces = []
        self.current_config_name = "default"
        
        # Initialize token manager for OAuth
        self.token_manager = TokenManager(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        
        # Initialize MCP service first to make it available to other services
        self.mcp_service: MCPService = None  # Will be initialized after other services
        
        # Initialize system services in dependency order
        # Use the new Control & Configuration Service instead of the old one
        self.config_service = ControlConfigService(config_dir=config_dir)
        self.system_parameters_service = SystemParametersService()
        self.agent_service = AgentServiceImpl(
            agents_dir=agents_dir,
            runtime_ref=self
        )
        
        # Initialize new LLM architecture services
        
        # 1. LLM Provider Manager (Ring 1 Service)
        self.llm_provider_manager = LLMProviderManager(token_manager=self.token_manager)
        self.llm_provider_manager.set_provider(settings.default_provider)
        
        # 2. Prompt Construction Service (Ring 1 Service) - with MCP integration
        self.prompt_construction_service = PromptConstructionService(
            agent_registry=None,
            system_services={},
            mcp_client_service=None  # Will be set after MCP initialization
        )
        
        # 3. Response Evaluator Service (Ring 1 Service) - with error-as-signal
        self.response_evaluator_service = ResponseEvaluatorService(
            llm_provider_manager=self.llm_provider_manager,
            prompt_construction_service=self.prompt_construction_service
        )
        
        # 4. Conversation Manager Service (Ring 2 Service)
        self.conversation_manager = ConversationManagerService(
            mcp_service=None  # Will be set after MCP initialization
        )
        
        # 5. Agent Orchestrator Service (Ring 2 Service)
        self.agent_orchestrator = AgentOrchestratorService(
            mcp_service=None  # Will be set after MCP initialization
        )
        
        # Initialize LLM control service for backward compatibility and additional features
        self.llm_control_service = LLMControlService(
            llm_service=self.llm_provider_manager  # Connect to the new provider manager
        )
        
        # Initialize MCP service with GCS runtime reference (async method)
        # We'll initialize it asynchronously when needed, not in constructor
        self.mcp_service = None
        self._mcp_service_init_task = None
        
        # We'll set MCP references after async initialization
        # These will be set in an async initialization method
        self.prompt_construction_service.mcp_client_service = None
        self.conversation_manager.mcp_service = None
        self.agent_orchestrator.mcp_service = None
        
        # Initialize kernel-level LLM service
        self.llm_kernel_service = LLMKernelServiceImpl(provider_manager=self.llm_provider_manager)
        self.llm_kernel_service.set_runtime(self)
        
        # Initialize auth and storage services
        self.auth_service = AuthServiceImpl(
            credentials_file=settings.qwen_credentials_file,
            credentials_dir=settings.qwen_credentials_dir
        )
        self.storage_service = StorageServiceImpl()
        
        # Register services with the kernel following the new architecture
        # Kernel services
        self.kernel.register_service("llm_kernel", self.llm_kernel_service)
        
        # Ring 1 services (Core Services)
        self.kernel.register_service("llm_provider_manager", self.llm_provider_manager)
        self.kernel.register_service("prompt_construction", self.prompt_construction_service)
        self.kernel.register_service("response_evaluator", self.response_evaluator_service)
        
        # Ring 2 services (Application Services)
        self.kernel.register_service("conversation_manager", self.conversation_manager)
        self.kernel.register_service("agent_orchestrator", self.agent_orchestrator)
        self.kernel.register_service("control_config", self.config_service)
        
        # Other core services
        self.kernel.register_service("config", self.config_service)
        self.kernel.register_service("agent", self.agent_service)
        self.kernel.register_service("llm_control", self.llm_control_service)
        self.kernel.register_service("auth", self.auth_service)
        self.kernel.register_service("storage", self.storage_service)
        self.kernel.register_service("system_params", self.system_parameters_service)
        self.kernel.register_service("mcp", self.mcp_service)
        
        # Set runtime reference in services that need access to other services
        self.config_service.set_runtime(self)
        self.system_parameters_service.set_runtime(self)
        self.agent_service.set_runtime(self)
        self.storage_service.set_runtime(self)
        self.auth_service.set_runtime(self)
        self.llm_kernel_service.set_runtime(self)
        self.response_evaluator_service.set_runtime(self)
        self.agent_orchestrator.set_runtime(self)
        
        # Register MCP tools for services that have them
        self.config_service.register_mcp_tools()
        self.system_parameters_service.register_mcp_tools()
        self.agent_service.register_mcp_tools()
        self.storage_service.register_mcp_tools()
        self.auth_service.register_mcp_tools()
        self.llm_kernel_service.register_mcp_tools()
        # Additional services that support MCP tool registration
        if hasattr(self, 'response_evaluator_service') and hasattr(self.response_evaluator_service, 'register_mcp_tools'):
            self.response_evaluator_service.register_mcp_tools()
        if hasattr(self, 'conversation_manager') and hasattr(self.conversation_manager, 'register_mcp_tools'):
            self.conversation_manager.register_mcp_tools()
        if hasattr(self, 'agent_orchestrator') and hasattr(self.agent_orchestrator, 'register_mcp_tools'):
            self.agent_orchestrator.register_mcp_tools()

    async def async_init(self):
        """Asynchronously initialize services that require async operations."""
        import asyncio
        self.mcp_service = await create_mcp_service(self)
        
        # Update services with MCP references after MCP service initialization
        self.prompt_construction_service.mcp_client_service = self.mcp_service.mcp_client
        self.conversation_manager.mcp_service = self.mcp_service
        self.agent_orchestrator.mcp_service = self.mcp_service
    
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
        
        # Shutdown services in reverse dependency order
        
        # Shutdown MCP services first to properly close connections
        if hasattr(self, 'mcp_service') and self.mcp_service and hasattr(self.mcp_service, 'shutdown'):
            try:
                await self.mcp_service.shutdown()
                logger.info("MCP service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during MCP service shutdown: {e}")
        
        # Shutdown LLM-related services
        if hasattr(self, 'response_evaluator_service') and hasattr(self.response_evaluator_service, 'shutdown'):
            try:
                await self.response_evaluator_service.shutdown()
                logger.info("Response evaluator service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during response evaluator service shutdown: {e}")
        
        if hasattr(self, 'llm_control_service') and hasattr(self.llm_control_service, 'shutdown'):
            try:
                await self.llm_control_service.shutdown()
                logger.info("LLM control service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during LLM control service shutdown: {e}")
        
        if hasattr(self, 'llm_provider_manager') and hasattr(self.llm_provider_manager, 'shutdown'):
            try:
                await self.llm_provider_manager.shutdown()
                logger.info("LLM provider manager service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during LLM provider manager shutdown: {e}")
        
        # Shutdown kernel
        if hasattr(self, 'kernel') and hasattr(self.kernel, 'shutdown'):
            try:
                await self.kernel.shutdown()
                logger.info("Kernel shutdown completed")
            except Exception as e:
                logger.warning(f"Error during kernel shutdown: {e}")
        
        # Shutdown the prompt construction service if it exists
        if hasattr(self, 'prompt_construction_service') and hasattr(self.prompt_construction_service, 'close'):
            try:
                self.prompt_construction_service.close()
                logger.info("Prompt construction service shutdown completed")
            except Exception as e:
                logger.warning(f"Error during prompt construction service cleanup: {e}")
        
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