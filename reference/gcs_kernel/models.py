"""
Data models for the GCS Kernel.

This module defines Pydantic models for all core data structures
used in the GCS Kernel, including tools, executions, resources, and events.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import uuid
from datetime import datetime


class ToolApprovalMode(str, Enum):
    DEFAULT = "DEFAULT"
    PLAN = "PLAN"
    AUTO_EDIT = "AUTO_EDIT"
    YOLO = "YOLO"


class ToolState(str, Enum):
    VALIDATING = "VALIDATING"
    SCHEDULED = "SCHEDULED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"


class ToolResult(BaseModel):
    """Standardized result for all tool executions"""
    tool_name: str
    llm_content: str = Field(description="Content sent back to the LLM")
    return_display: str = Field(description="Content shown to the user")
    success: bool = True
    error: Optional[str] = None


class ToolDefinition(BaseModel):
    """Definition of a tool with schema and metadata"""
    name: str
    display_name: str
    description: str
    parameter_schema: Dict[str, Any]
    approval_required: bool = True
    approval_mode: ToolApprovalMode = ToolApprovalMode.DEFAULT


class ToolExecution(BaseModel):
    """Represents a single tool execution instance"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    parameters: Dict[str, Any]
    state: ToolState = ToolState.VALIDATING
    approved: bool = False
    approval_mode: ToolApprovalMode = ToolApprovalMode.DEFAULT
    result: Optional[ToolResult] = None
    created_at: datetime = Field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tool_definition: Optional[ToolDefinition] = None


class ResourceQuota(BaseModel):
    """Resource allocation and quota enforcement"""
    cpu_limit: Optional[float] = None  # Percentage of CPU
    memory_limit: Optional[int] = None  # Memory in bytes
    max_concurrent_executions: int = 10
    max_execution_time: int = 300  # in seconds


class Event(BaseModel):
    """Event in the kernel's event loop"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class MCPConfig(BaseModel):
    """Configuration for MCP (Model Context Protocol) server/client"""
    server_url: str = Field(description="URL for the MCP server")
    client_id: Optional[str] = Field(default=None, description="Client identifier for authentication")
    client_secret: Optional[str] = Field(default=None, description="Client secret for authentication")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    request_timeout: int = Field(default=60, description="Request timeout in seconds")