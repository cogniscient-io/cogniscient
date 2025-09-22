"""FastAPI backend for the LLM Orchestration Frontend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import backend components with absolute imports
from src.orchestrator.chat_interface import ChatInterface
from src.orchestrator.llm_orchestrator import LLMOrchestrator
from src.ucs_runtime import UCSRuntime

# Pydantic models for request/response validation
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Dict[str, str]]

class StatusResponse(BaseModel):
    agents: List[str]
    agent_configs: Dict[str, Any]
    agent_last_calls: Dict[str, Dict[str, Any]]
    system_status: str

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

@app.on_event("startup")
async def startup_event():
    """Initialize backend components on startup."""
    global ucs_runtime, orchestrator, chat_interface
    
    # Initialize backend components
    ucs_runtime = UCSRuntime()
    ucs_runtime.load_all_agents()
    orchestrator = LLMOrchestrator(ucs_runtime)
    chat_interface = ChatInterface(orchestrator)

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
    
    # Return information about loaded agents and system state
    return StatusResponse(
        agents=list(ucs_runtime.agents.keys()),
        agent_configs=ucs_runtime.agent_configs,
        agent_last_calls=ucs_runtime.agent_last_call,
        system_status="running"
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat messages."""
    if chat_interface is None:
        return ChatResponse(
            response="System is still initializing. Please try again in a moment.",
            conversation_history=[]
        )
    
    user_message = request.message
    
    # Process user input through chat interface
    response = await chat_interface.process_user_input(user_message)
    
    return ChatResponse(
        response=response,
        conversation_history=chat_interface.conversation_history
    )