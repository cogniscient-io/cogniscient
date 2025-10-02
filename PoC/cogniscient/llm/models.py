"""
Models for Qwen LLM integration.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class QwenMessage(BaseModel):
    """Represents a message in the Qwen chat format."""
    role: str  # 'system', 'user', or 'assistant'
    content: str


class QwenChatRequest(BaseModel):
    """Request model for Qwen chat completions."""
    model: str
    messages: List[QwenMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0
    logit_bias: Optional[Dict[str, float]] = None


class QwenChatResponse(BaseModel):
    """Response model from Qwen chat completions."""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, Any]  # Changed from Dict[str, int] to Dict[str, Any] to handle nested structures


class QwenCompletionResponse(BaseModel):
    """Response model from Qwen text completions."""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, Any]  # Changed from Dict[str, int] to Dict[str, Any] to handle nested structures