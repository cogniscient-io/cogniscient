"""
Data models for the GCS Kernel.

This module defines Pydantic models for all core data structures
used in the GCS Kernel, including tools, executions, resources, and events.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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
    """Definition of a tool with schema and metadata. Uses OpenAI-compatible format."""
    # The tool definition itself should match the OpenAI function format
    type: str = "function"  # OpenAI uses type="function" for function tools
    function: Dict[str, Any]  # Contains name, description, and parameters
    approval_required: bool = True
    approval_mode: ToolApprovalMode = ToolApprovalMode.DEFAULT
    
    @property
    def name(self) -> str:
        """Convenience property to access the function name."""
        return self.function.get("name", "")
    
    @property 
    def display_name(self) -> str:
        """Convenience property to access the display name."""
        # Try to get display_name from function if available, otherwise use name
        return self.function.get("display_name", self.function.get("name", ""))
    
    @property
    def description(self) -> str:
        """Convenience property to access the function description."""
        return self.function.get("description", "")
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """Convenience property to access the function parameters."""
        return self.function.get("parameters", {})
    
    @classmethod
    def create(cls, name: str, description: str, parameters: Dict[str, Any], 
               display_name: str = None, approval_required: bool = True,
               approval_mode: ToolApprovalMode = ToolApprovalMode.DEFAULT):
        """
        Create a ToolDefinition in OpenAI-compatible format.
        
        Args:
            name: The name of the tool
            description: The description of the tool
            parameters: The parameters in OpenAI format
            display_name: Optional display name (defaults to name)
            approval_required: Whether this tool requires approval
            approval_mode: The approval mode for this tool
        """
        function_data = {
            "name": name,
            "description": description,
            "parameters": parameters
        }
        if display_name:
            function_data["display_name"] = display_name
            
        return cls(
            function=function_data,
            approval_required=approval_required,
            approval_mode=approval_mode
        )


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
    runtime_data_directory: str = Field(default="./runtime_data", description="Directory to store runtime data including MCP server registry")
    server_registry_filename: str = Field(default="mcp_servers.json", description="Filename for the MCP server registry file")


class ToolInclusionPolicy(str, Enum):
    """
    Enum defining different strategies for tool inclusion in LLM prompts.
    """
    ALL_AVAILABLE = "all_available"  # Include all available tools
    NONE = "none"  # Don't include any tools
    CONTEXTUAL_SUBSET = "contextual_subset"  # Include tools based on contextual analysis
    CUSTOM = "custom"  # Include a custom subset specified by the caller


class ToolInclusionConfig(BaseModel):
    """
    Configuration for tool inclusion strategy.
    """
    prompt_id: str
    policy: ToolInclusionPolicy
    custom_tools: Optional[List[Dict[str, Any]]] = None
    context_info: Optional[Dict[str, Any]] = None  # Additional context for contextual policy


class PromptStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    ERROR = "error"


class PromptObject(BaseModel):
    # Core prompt information
    prompt_id: str = Field(description="Unique identifier for the prompt")
    content: str = Field(description="The actual prompt text from user")
    role: str = Field(default="user", description="Role of the prompt in conversation")
    
    # Tool configuration
    tool_policy: ToolInclusionPolicy = Field(default=ToolInclusionPolicy.ALL_AVAILABLE)
    custom_tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Custom tools for this prompt")
    
    # Conversation history
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Complete conversation history")
    
    # Execution context
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for processing")
    user_id: Optional[str] = Field(default=None, description="User identifier if authenticated")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # Execution metadata
    status: PromptStatus = Field(default=PromptStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = Field(default=None)
    
    # Processing results
    result_content: Optional[str] = Field(default=None, description="Processed content result")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tool calls made during processing")
    tool_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results from tool executions")
    error_message: Optional[str] = Field(default=None, description="Error message if status is ERROR")
    
    # Configuration
    streaming_enabled: bool = Field(default=True, description="Whether to stream the response")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    tool_choice: str = Field(default="auto", description="Tool choice strategy")
    temperature: float = Field(default=0.7, description="Temperature setting for generation")
    
    @classmethod
    def create(cls, 
               content: str,
               prompt_id: str = None,
               role: str = "user",
               tool_policy: ToolInclusionPolicy = ToolInclusionPolicy.ALL_AVAILABLE,
               custom_tools: Optional[List[Dict[str, Any]]] = None,
               conversation_history: List[Dict[str, Any]] = None,
               user_id: str = None,
               session_id: str = None,
               streaming_enabled: bool = True,
               max_tokens: int = None,
               tool_choice: str = "auto",
               temperature: float = 0.7) -> 'PromptObject':
        """
        Create a new PromptObject with sensible defaults.
        
        Args:
            content: The prompt text from user
            prompt_id: Optional unique identifier (auto-generated if not provided)
            role: Role of the prompt in conversation (default: "user")
            tool_policy: Tool inclusion policy (default: ALL_AVAILABLE)
            custom_tools: Custom tools for this prompt
            conversation_history: Complete conversation history
            user_id: User identifier if authenticated
            session_id: Session identifier
            streaming_enabled: Whether to stream the response (default: True)
            max_tokens: Maximum tokens to generate
            temperature: Temperature setting for generation (default: 0.7)
            
        Returns:
            A new PromptObject instance
        """
        import uuid
        
        return cls(
            prompt_id=prompt_id or f"prompt_{str(uuid.uuid4())}",
            content=content,
            role=role,
            tool_policy=tool_policy,
            custom_tools=custom_tools,
            conversation_history=conversation_history or [],
            user_id=user_id,
            session_id=session_id,
            streaming_enabled=streaming_enabled,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    @classmethod
    def from_string(cls, 
                    prompt: str,
                    system_context: str = None,
                    prompt_id: str = None,
                    tool_policy: ToolInclusionPolicy = ToolInclusionPolicy.ALL_AVAILABLE,
                    custom_tools: List[Dict[str, Any]] = None) -> 'PromptObject':
        """
        Create a PromptObject from a simple string prompt, with optional system context.
        
        Args:
            prompt: The user's input prompt
            system_context: Optional system context to include
            prompt_id: Optional unique identifier (auto-generated if not provided)
            tool_policy: Tool inclusion policy (default: ALL_AVAILABLE)
            custom_tools: Custom tools for this prompt
            
        Returns:
            A new PromptObject instance with proper conversation history
        """
        import uuid
        
        # Prepare conversation history with system context if provided
        conversation_history = []
        if system_context:
            conversation_history.append({"role": "system", "content": system_context})
        
        return cls(
            prompt_id=prompt_id or f"prompt_{str(uuid.uuid4())}",
            content=prompt,
            tool_policy=tool_policy,
            custom_tools=custom_tools,
            conversation_history=conversation_history
        )
    
    @classmethod
    def for_tool_result(cls,
                       tool_result: Any,
                       conversation_history: List[Dict[str, Any]] = None,
                       prompt_id: str = None) -> 'PromptObject':
        """
        Create a PromptObject specifically for processing a tool result.
        
        Args:
            tool_result: The tool result to process
            conversation_history: The conversation history to maintain context
            prompt_id: Optional unique identifier (auto-generated if not provided)
            
        Returns:
            A new PromptObject instance configured for tool result processing
        """
        import uuid
        
        prompt_obj = cls(
            prompt_id=prompt_id or f"tool_result_{str(uuid.uuid4())}",
            content=f"Process this tool result: {tool_result}",
            role="tool",
            conversation_history=conversation_history or [],
            tool_policy=ToolInclusionPolicy.ALL_AVAILABLE
        )
        
        # Add the tool result to the conversation history
        tool_message = {
            "role": "tool",
            "content": str(getattr(tool_result, 'llm_content', tool_result)),
            "tool_result": tool_result
        }
        prompt_obj.conversation_history.append(tool_message)
        
        return prompt_obj
    
    def add_message_to_history(self, role: str, content: str, **kwargs):
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message ('user', 'assistant', 'system', 'tool')
            content: The content of the message
            **kwargs: Additional message properties
        """
        message = {
            "role": role,
            "content": content
        }
        message.update(kwargs)  # Add any additional properties
        self.conversation_history.append(message)
        self.updated_at = datetime.now()
    
    def add_system_message(self, content: str):
        """Add a system message to the conversation history."""
        self.add_message_to_history("system", content)
    
    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self.add_message_to_history("user", content)
    
    def add_assistant_message(self, content: str, tool_calls: List[Dict[str, Any]] = None):
        """Add an assistant message to the conversation history."""
        message = {
            "role": "assistant",
            "content": content
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.conversation_history.append(message)
        self.updated_at = datetime.now()
    
    def add_tool_message(self, content: str, tool_call_id: str = None):
        """Add a tool message to the conversation history."""
        message = {
            "role": "tool",
            "content": content
        }
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.conversation_history.append(message)
        self.updated_at = datetime.now()
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message from the conversation history."""
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "user":
                return msg.get("content")
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message from the conversation history."""
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "assistant":
                return msg.get("content")
        return None
    
    def has_tool_calls(self) -> bool:
        """Check if the prompt object has any tool calls."""
        return len(self.tool_calls) > 0
    
    def has_tool_results(self) -> bool:
        """Check if the prompt object has any tool results."""
        return len(self.tool_results) > 0
    
    def clone(self) -> 'PromptObject':
        """Create a deep copy of the prompt object."""
        import copy
        return copy.deepcopy(self)
    
    def mark_processing(self):
        """Mark the prompt as being processed"""
        self.status = PromptStatus.PROCESSING
        self.updated_at = datetime.now()
    
    def mark_completed(self, content: str):
        """Mark the prompt as completed with result content"""
        self.status = PromptStatus.COMPLETED
        self.result_content = content
        self.processed_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_error(self, error_msg: str):
        """Mark the prompt as having an error"""
        self.status = PromptStatus.ERROR
        self.error_message = error_msg
        self.updated_at = datetime.now()
    
    def add_tool_call(self, tool_call: Dict[str, Any]):
        """Add a tool call to the prompt object"""
        self.tool_calls.append(tool_call)
        self.updated_at = datetime.now()
    
    def add_tool_result(self, tool_result: Dict[str, Any]):
        """Add a tool result to the prompt object"""
        self.tool_results.append(tool_result)
        self.updated_at = datetime.now()