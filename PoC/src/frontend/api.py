"""FastAPI backend for the LLM Orchestration Frontend."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import json
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import backend components with absolute imports
from src.orchestrator.chat_interface import ChatInterface
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.ucs_runtime import UCSRuntime
from src.config.settings import settings

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

# Initialize FastAPI app
app = FastAPI(title="LLM Orchestration Frontend API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global variables for backend components
ucs_runtime = None
orchestrator = None
chat_interface = None

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


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up backend components on shutdown."""
    global ucs_runtime
    
    if ucs_runtime:
        # Stop health monitoring for external agents
        await ucs_runtime.agent_loader.external_agent_registry.stop_health_checks()
        
        # Shutdown all agents
        ucs_runtime.shutdown()

@app.on_event("startup")
async def startup_event():
    """Initialize backend components on startup."""
    global ucs_runtime, orchestrator, chat_interface
    
    # Initialize backend components
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_all_agents()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Start health monitoring for external agents
    await ucs_runtime.agent_loader.external_agent_registry.start_health_checks()

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
    if ucs_runtime is None:
        return StatusResponse(
            agents=[],
            agent_configs={},
            agent_last_calls={},
            system_status="initializing"
        )
    
    # Get system parameters if SystemParametersManager is available
    system_parameters = {}
    if "SystemParametersManager" in ucs_runtime.agents:
        try:
            params_result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
            if params_result.get("status") == "success":
                system_parameters = params_result.get("parameters", {})
        except Exception:
            pass
    
    # Return information about loaded agents and system state
    return StatusResponse(
        agents=list(ucs_runtime.agents.keys()),
        agent_configs=ucs_runtime.agent_configs,
        agent_last_calls=ucs_runtime.agent_last_call,
        system_status="running",
        system_parameters=system_parameters
    )

@app.get("/api/system_parameters", response_model=SystemParameterResponse)
async def get_system_parameters():
    """Get current system parameters."""
    if ucs_runtime is None or "SystemParametersManager" not in ucs_runtime.agents:
        return SystemParameterResponse(
            status="error",
            message="SystemParametersManager not available",
            parameters={}
        )
    
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "get_system_parameters")
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
    if ucs_runtime is None or "SystemParametersManager" not in ucs_runtime.agents:
        return SystemParameterResponse(
            status="error",
            message="SystemParametersManager not available",
            parameters={}
        )
    
    try:
        result = ucs_runtime.run_agent("SystemParametersManager", "set_system_parameter",
                                     parameter_name=parameter_update.parameter_name,
                                     parameter_value=parameter_update.parameter_value)
        return SystemParameterResponse(**result)
    except Exception as e:
        return SystemParameterResponse(
            status="error",
            message=f"Failed to set system parameter: {str(e)}",
            parameters={}
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat messages."""
    if chat_interface is None:
        return ChatResponse(
            response="System is still initializing. Please try again in a moment.",
            tool_calls=[],
            suggested_agents=[],
            conversation_history=[]
        )
    
    user_message = request.message
    
    # Process user input through chat interface
    result = await chat_interface.process_user_input(user_message)
    
    # Handle both old and new response formats
    if isinstance(result, str):
        # Old format - just a string response
        response_text = result
        tool_calls = []
        suggested_agents = []
    else:
        # New format - dictionary with response and tool calls
        response_text = result.get("response", "")
        tool_calls = result.get("tool_calls", [])
        suggested_agents = result.get("suggested_agents", [])
    
    return ChatResponse(
        response=response_text,
        tool_calls=tool_calls,
        suggested_agents=suggested_agents,
        conversation_history=chat_interface.conversation_history
    )

@app.post("/api/stream_chat")
async def stream_chat(request: ChatRequest):
    """Process chat messages with streaming response."""
    if chat_interface is None:
        def error_generator():
            event = {"type": "assistant_response", "content": "System is still initializing. Please try again in a moment."}
            yield f"data: {json.dumps(event)}\n\n"
            yield f"data: [DONE]\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")
    
    # Create an asyncio queue to handle communication between the processing task and the response generator
    event_queue = asyncio.Queue()
    
    async def send_stream_event(event_type: str, content: str = None, data: Dict[str, Any] = None):
        event = {
            "type": event_type,
        }
        if content is not None:
            event["content"] = content
        if data is not None:
            event["data"] = data
        
        await event_queue.put(event)
    
    async def process_request():
        """Background task to process the request and send events to the queue."""
        try:
            # Add user input to conversation history
            chat_interface.conversation_history.append({"role": "user", "content": request.message})
            
            # Process user input through chat interface with streaming
            await chat_interface.process_user_input_streaming(
                request.message, 
                chat_interface.conversation_history, 
                send_stream_event
            )
            
            # Send final response with updated conversation history
            final_event = {
                "type": "final_response",
                "data": {
                    "conversation_history": chat_interface.conversation_history
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
        yield f"data: [DONE]\n\n"
        
        # Wait for the processing task to complete
        await task
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# External Agent Registration Endpoints
@app.post("/api/agents/external/register", response_model=ExternalAgentResponse)
async def register_external_agent(agent_request: ExternalAgentRequest, api_key: str = Depends(verify_api_key)):
    """Register a new external agent via REST API."""
    if ucs_runtime is None:
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
        
        # Attempt to validate the agent endpoint before registration
        validation_result = await ucs_runtime.agent_loader.external_agent_registry.validate_agent_endpoint(agent_config)
        if validation_result["status"] != "success":
            return ExternalAgentResponse(
                status="error",
                message=f"Failed to validate agent endpoint: {validation_result['message']}"
            )
        
        # Register the external agent
        registration_success = ucs_runtime.agent_loader.register_external_agent(agent_config)
        
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
    if ucs_runtime is None:
        return ExternalAgentResponse(
            status="error",
            message="System is not initialized"
        )
    
    try:
        # Deregister the external agent
        deregistration_success = ucs_runtime.agent_loader.deregister_external_agent(agent_name)
        
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
    if ucs_runtime is None:
        return ExternalAgentListResponse(
            status="error",
            agents=[]
        )
    
    try:
        # Get registered external agents from the registry
        external_agent_names = ucs_runtime.agent_loader.external_agent_registry.list_agents()
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
    if ucs_runtime is None:
        return ExternalAgentResponse(
            status="error",
            message="System is not initialized"
        )
    
    try:
        # Get the agent configuration
        agent_config = ucs_runtime.agent_loader.external_agent_registry.get_agent_config(agent_name)
        
        if agent_config:
            return ExternalAgentResponse(
                status="success",
                message=f"Found external agent: {agent_name}",
                agent_info=agent_config
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
    if ucs_runtime is None:
        return HealthCheckResponse(
            status="error",
            health_status="unknown",
            error_message="System is not initialized"
        )
    
    try:
        # Get health status from the registry
        health_info = await ucs_runtime.agent_loader.external_agent_registry.get_agent_health(agent_name)
        
        if health_info:
            return HealthCheckResponse(
                status="success",
                health_status=health_info["health_status"],
                last_check=health_info["last_health_check"],
                error_message=health_info.get("health_status_error")
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