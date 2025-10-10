"""FastAPI backend for the LLM Orchestration Frontend."""

# Standard library imports
import asyncio
import json
import os

# Third-party imports
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Import backend components from the installed cogniscient package
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.config.settings import settings

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    suggested_agents: List[Dict[str, Any]] = []
    conversation_history: List[Dict[str, str]]

# Streaming response event
class StreamEvent(BaseModel):
    type: str  # assistant_response, tool_call, tool_response, suggested_agents, final_response
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class StatusResponse(BaseModel):
    agents: List[str]
    agent_configs: Dict[str, Any]
    agent_last_calls: Dict[str, Dict[str, Any]]
    system_status: str
    system_parameters: Dict[str, Any] = {}

class SystemParameterUpdate(BaseModel):
    parameter_name: str
    parameter_value: str

class SystemParameterResponse(BaseModel):
    status: str
    message: str
    parameters: Dict[str, Any] = {}

# Pydantic models for external agent registration
class ExternalAgentRequest(BaseModel):
    name: str
    description: str
    version: str
    endpoint_url: str
    methods: Dict[str, Dict]
    authentication: Optional[Dict] = None
    health_check_url: Optional[str] = None
    settings: Optional[Dict] = None

class ExternalAgentResponse(BaseModel):
    status: str
    message: str
    agent_info: Optional[Dict[str, Any]] = None

class ExternalAgentListResponse(BaseModel):
    status: str
    agents: List[str]

class HealthCheckResponse(BaseModel):
    status: str
    health_status: str
    last_check: Optional[float] = None
    error_message: Optional[str] = None

# Global variables for backend components
gcs_runtime = None
orchestrator = None
chat_interface = None

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    # We'll mount static files in the lifespan manager after app initialization
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events."""
    global gcs_runtime, orchestrator, chat_interface
    
    # Startup: Initialize backend components
    # Import settings to get config and agents directories
    from cogniscient.engine.config.settings import settings
    
    # Initialize backend components
    gcs_runtime = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    gcs_runtime.load_all_agents()
    orchestrator = LLMOrchestrator(gcs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Register orchestrator and chat interface with the kernel for central management
    gcs_runtime.set_llm_orchestrator(orchestrator)
    gcs_runtime.register_chat_interface(chat_interface)
    
    # Start health monitoring for external agents via MCP service
    await gcs_runtime.mcp_service.mcp_client.mcp_registry.start_health_checks()
    
    # Mount static files after initialization
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    yield
    
    # Shutdown: Clean up backend components
    if gcs_runtime:
        # Stop health monitoring for external agents via MCP service
        await gcs_runtime.mcp_service.mcp_client.mcp_registry.stop_health_checks()
        
        # Shutdown all agents
        gcs_runtime.shutdown()

# Initialize FastAPI app with lifespan manager
app = FastAPI(title="LLM Orchestration Frontend API", version="0.1.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security setup
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the API key for protected endpoints."""
    # In a real implementation, you would validate against a secure store of API keys
    # For this demo, we'll use a fixed key from settings
    expected_api_key = getattr(settings, "EXTERNAL_AGENT_REGISTRATION_API_KEY", "demo-key-for-external-agent-registration")
    
    if credentials.credentials != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return credentials.credentials

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML file."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    return HTMLResponse(content="<h1>LLM Orchestration Frontend</h1>", status_code=200)

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Get system status information."""
    if gcs_runtime is None:
        return StatusResponse(
            agents=[],
            agent_configs={},
            agent_last_calls={},
            system_status="initializing"
        )
    
    # Get system parameters from the system parameters service
    try:
        params_result = gcs_runtime.system_parameters_service.get_system_parameters()
        if params_result.get("status") == "success":
            system_parameters = params_result.get("parameters", {})
    except Exception:
        pass
    
    # Return information about loaded agents and system state
    return StatusResponse(
        agents=list(gcs_runtime.agents.keys()),
        agent_configs=gcs_runtime.agent_configs,
        agent_last_calls=gcs_runtime.agent_last_call,
        system_status="running",
        system_parameters=system_parameters
    )

@app.get("/api/system_parameters", response_model=SystemParameterResponse)
async def get_system_parameters():
    """Get current system parameters."""
    if gcs_runtime is None:
        return SystemParameterResponse(
            status="error",
            message="System is not initialized",
            parameters={}
        )
    
    try:
        result = gcs_runtime.system_parameters_service.get_system_parameters()
        return SystemParameterResponse(**result)
    except Exception as e:
        return SystemParameterResponse(
            status="error",
            message=f"Failed to get system parameters: {str(e)}",
            parameters={}
        )

@app.post("/api/system_parameters", response_model=SystemParameterResponse)
async def set_system_parameter(parameter_update: SystemParameterUpdate):
    """Set a system parameter."""
    if gcs_runtime is None:
        return SystemParameterResponse(
            status="error",
            message="System is not initialized",
            parameters={}
        )
    
    try:
        result = gcs_runtime.system_parameters_service.set_system_parameter(
            parameter_name=parameter_update.parameter_name,
            parameter_value=parameter_update.parameter_value)
        return SystemParameterResponse(**result)
    except Exception as e:
        return SystemParameterResponse(
            status="error",
            message=f"Failed to set system parameter: {str(e)}",
            parameters={}
        )



@app.post("/api/stream_chat")
async def stream_chat(request: ChatRequest):
    """Process chat messages with streaming response via the kernel."""
    if gcs_runtime is None or not hasattr(gcs_runtime, 'kernel'):
        def error_generator():
            event = {"type": "assistant_response", "content": "System is still initializing. Please try again in a moment."}
            yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    # Create an asyncio queue to handle communication between the processing task and the response generator
    event_queue = asyncio.Queue()
    
    def send_stream_event(event_type: str, content: str = None, data: Dict[str, Any] = None):
        event = {
            "type": event_type,
        }
        if content is not None:
            event["content"] = content
        if data is not None:
            event["data"] = data
        
        # Put the event in the queue (we need to ensure this runs in the event loop)
        asyncio.create_task(event_queue.put(event))
    
    # Add the streaming callback to the kernel
    gcs_runtime.kernel.add_streaming_callback(send_stream_event)
    
    async def process_request():
        """Background task to process the request through the kernel and send events to the queue."""
        try:
            # Process user input through the kernel with streaming
            result = await gcs_runtime.kernel.process_user_input_streaming(request.message)
            
            # Send final response with updated conversation history from the kernel
            final_event = {
                "type": "final_response",
                "data": {
                    "conversation_history": gcs_runtime.kernel.get_conversation_history(),
                    "result": result
                }
            }
            await event_queue.put(final_event)
            
        except Exception as e:
            error_event = {"type": "assistant_response", "content": f"Error processing your request: {str(e)}"}
            await event_queue.put(error_event)
        finally:
            # Signal completion
            await event_queue.put(None)  # None signals end of stream
    
    async def event_generator():
        """Generator that yields events from the queue."""
        # Start the background processing task
        task = asyncio.create_task(process_request())
        
        # Yield events from the queue as they come in
        while True:
            event = await event_queue.get()
            if event is None:  # End signal
                break
            yield f"data: {json.dumps(event)}\n\n"
        
        # Signal end of stream
        yield "data: [DONE]\n\n"
        
        # Wait for the processing task to complete
        await task
    
    return StreamingResponse(event_generator(), media_type="text-event-stream")

# External Agent Registration Endpoints
@app.post("/api/agents/external/register", response_model=ExternalAgentResponse)
async def register_external_agent(agent_request: ExternalAgentRequest, api_key: str = Depends(verify_api_key)):
    """Register a new external agent via REST API."""
    if gcs_runtime is None:
        return ExternalAgentResponse(
            status="error",
            message="System is not initialized"
        )
    
    try:
        # Prepare the agent configuration
        agent_config = {
            "name": agent_request.name,
            "description": agent_request.description,
            "version": agent_request.version,
            "endpoint_url": agent_request.endpoint_url,
            "methods": agent_request.methods,
            "enabled": True
        }
        
        if agent_request.authentication:
            agent_config["authentication"] = agent_request.authentication
            
        if agent_request.health_check_url:
            agent_config["health_check_url"] = agent_request.health_check_url
            
        if agent_request.settings:
            agent_config["settings"] = agent_request.settings
        
        # Prepare connection parameters for MCP
        connection_params = {
            "type": "stdio",  # Default to stdio, can be overridden by agent_request
            "command": agent_config["endpoint_url"],  # This may need to be parsed differently 
        }
        
        if agent_config.get("settings"):
            connection_params.update(agent_config["settings"])
        
        # Register the external agent via MCP service
        registration_result = await gcs_runtime.mcp_service.connect_to_external_agent(
            agent_config["name"], 
            connection_params
        )
        
        registration_success = registration_result.get("success", False)
        if not registration_success:
            return ExternalAgentResponse(
                status="error",
                message=f"Failed to register external agent: {registration_result.get('message', 'Unknown error')}"
            )
        
        if registration_success:
            return ExternalAgentResponse(
                status="success",
                message=f"Successfully registered external agent: {agent_request.name}",
                agent_info=agent_config
            )
        else:
            return ExternalAgentResponse(
                status="error",
                message=f"Failed to register external agent: {agent_request.name}"
            )
    except Exception as e:
        return ExternalAgentResponse(
            status="error",
            message=f"Exception during external agent registration: {str(e)}"
        )

@app.delete("/api/agents/external/{agent_name}", response_model=ExternalAgentResponse)
async def deregister_external_agent(agent_name: str, api_key: str = Depends(verify_api_key)):
    """Deregister an external agent via REST API."""
    if gcs_runtime is None:
        return ExternalAgentResponse(
            status="error",
            message="System is not initialized"
        )
    
    try:
        # Deregister the external agent via MCP service
        deregistration_result = await gcs_runtime.mcp_service.disconnect_from_external_agent(agent_name)
        deregistration_success = deregistration_result.get("success", False)
        
        if deregistration_success:
            return ExternalAgentResponse(
                status="success",
                message=f"Successfully deregistered external agent: {agent_name}"
            )
        else:
            return ExternalAgentResponse(
                status="error",
                message=f"Failed to deregister external agent: {agent_name} (agent not found or other error)"
            )
    except Exception as e:
        return ExternalAgentResponse(
            status="error",
            message=f"Exception during external agent deregistration: {str(e)}"
        )

@app.get("/api/agents/external", response_model=ExternalAgentListResponse)
async def list_external_agents():
    """List all registered external agents."""
    if gcs_runtime is None:
        return ExternalAgentListResponse(
            status="error",
            agents=[]
        )
    
    try:
        # Get registered external agents via MCP service
        connected_agents_result = gcs_runtime.mcp_service.get_connected_agents()
        external_agent_names = connected_agents_result.get('connected_agents', [])
        return ExternalAgentListResponse(
            status="success",
            agents=external_agent_names
        )
    except Exception as e:
        return ExternalAgentListResponse(
            status="error",
            message=f"Exception during listing external agents: {str(e)}",
            agents=[]
        )

@app.get("/api/agents/external/{agent_name}", response_model=ExternalAgentResponse)
async def get_external_agent(agent_name: str):
    """Get details about a specific external agent."""
    if gcs_runtime is None:
        return ExternalAgentResponse(
            status="error",
            message="System is not initialized"
        )
    
    try:
        # Get the agent configuration via MCP service
        capabilities_result = await gcs_runtime.mcp_service.get_external_agent_capabilities(agent_name)
        
        if capabilities_result["success"]:
            agent_info = {
                "name": agent_name,
                "capabilities": capabilities_result.get("capabilities", [])
            }
            return ExternalAgentResponse(
                status="success",
                message=f"Found external agent: {agent_name}",
                agent_info=agent_info
            )
        else:
            return ExternalAgentResponse(
                status="error",
                message=f"External agent not found: {agent_name}"
            )
    except Exception as e:
        return ExternalAgentResponse(
            status="error",
            message=f"Exception during getting external agent: {str(e)}"
        )

@app.get("/api/agents/external/{agent_name}/health", response_model=HealthCheckResponse)
async def get_external_agent_health(agent_name: str):
    """Check health status of an external agent."""
    if gcs_runtime is None:
        return HealthCheckResponse(
            status="error",
            health_status="unknown",
            error_message="System is not initialized"
        )
    
    try:
        # Note: MCP doesn't have the same health check functionality
        # For now, we'll check if the agent is connected
        connected_agents_result = gcs_runtime.mcp_service.get_connected_agents()
        connected_agents = connected_agents_result.get('connected_agents', [])
        
        if agent_name in connected_agents:
            return HealthCheckResponse(
                status="success",
                health_status="connected",
                error_message=None
            )
        else:
            return HealthCheckResponse(
                status="error",
                health_status="not_found",
                error_message=f"External agent not found: {agent_name}"
            )
    except Exception as e:
        return HealthCheckResponse(
            status="error",
            health_status="unknown",
            error_message=f"Exception during health check: {str(e)}"
        )