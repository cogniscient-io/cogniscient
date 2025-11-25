"""
Tool Call Streaming Service for GCS Kernel

This module implements a robust tool call streaming parser based on sophisticated
parsing techniques from Qwen Code, handling fragmented JSON, index collisions,
and complex tool call states during streaming responses from LLM providers.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from gcs_kernel.tool_call_model import ToolCall


logger = logging.getLogger(__name__)


@dataclass
class ToolCallParseResult:
    """Result of parsing a tool call chunk"""
    complete: bool
    value: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    repaired: bool = False


@dataclass
class ToolCallState:
    """State tracking for a single tool call during streaming"""
    buffer: str = ""
    depth: int = 0
    in_string: bool = False
    escape_next: bool = False
    id: Optional[str] = None
    name: Optional[str] = None


class ToolCallStreamingService:
    """
    A service for processing streaming tool call chunks from LLM responses.
    Handles complex scenarios like fragmented JSON, index collisions, 
    multiple concurrent tool calls, and JSON repair.
    """
    
    def __init__(self):
        # Maps operation ID to its parsers
        self.operation_parsers: Dict[str, StreamingToolCallParser] = {}
    
    def get_parser(self, operation_id: str) -> 'StreamingToolCallParser':
        """
        Get or create a parser for the specified operation.
        
        Args:
            operation_id: Unique identifier for the streaming operation
            
        Returns:
            StreamingToolCallParser instance for this operation
        """
        if operation_id not in self.operation_parsers:
            self.operation_parsers[operation_id] = StreamingToolCallParser()
        return self.operation_parsers[operation_id]
    
    def process_streaming_chunk(self, chunk_data: Dict[str, Any], operation_id: str) -> List[Dict[str, Any]]:
        """
        Process a streaming chunk containing potential tool calls.
        
        Args:
            chunk_data: Raw chunk from streaming response
            operation_id: Operation identifier for parser state
            
        Returns:
            List of completed tool calls if any are finished
        """
        parser = self.get_parser(operation_id)
        choices = chunk_data.get("choices", [])
        
        if not choices:
            return []
        
        tool_calls_delta = choices[0].get("delta", {}).get("tool_calls", [])
        if not tool_calls_delta:
            return []
        
        # Process each tool call delta in the chunk
        completed_tool_calls = []
        for tool_call_delta in tool_calls_delta:
            index = tool_call_delta.get("index", 0)
            
            # Extract delta components
            tc_id = tool_call_delta.get("id")
            function_delta = tool_call_delta.get("function", {})
            func_name = function_delta.get("name")
            func_args_delta = function_delta.get("arguments", "")
            
            # Add chunk to parser
            result = parser.add_chunk(index, func_args_delta, tc_id, func_name)
            
            # If complete tool call is detected, add it to results
            if result.complete and result.value:
                completed_tool_calls.append({
                    "id": result.value.get("id", tc_id or ""),
                    "type": "function",
                    "function": {
                        "name": result.value.get("name", func_name or ""),
                        "arguments": json.dumps(result.value.get("arguments", {}))
                    }
                })
        
        return completed_tool_calls
    
    def get_partial_tool_calls(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get all partially built tool calls for an operation.
        
        Args:
            operation_id: Operation identifier
            
        Returns:
            List of incomplete tool calls
        """
        if operation_id not in self.operation_parsers:
            return []
        
        parser = self.operation_parsers[operation_id]
        return parser.get_incomplete_tool_calls()
    
    def get_completed_tool_calls(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get completed tool calls for an operation and reset parser state.

        Args:
            operation_id: Operation identifier

        Returns:
            List of completed tool calls
        """
        if operation_id not in self.operation_parsers:
            return []

        parser = self.operation_parsers[operation_id]
        completed_calls = parser.get_completed_tool_calls()

        # Reset the parser after getting completed calls
        del self.operation_parsers[operation_id]

        return completed_calls

    def peek_completed_tool_calls(self, operation_id: str) -> List[Dict[str, Any]]:
        """
        Get completed tool calls for an operation without resetting parser state.
        This is useful when you want to access completed calls without removing them.

        Args:
            operation_id: Operation identifier

        Returns:
            List of completed tool calls
        """
        if operation_id not in self.operation_parsers:
            return []

        parser = self.operation_parsers[operation_id]
        return parser.get_completed_tool_calls()
    
    def reset_parser(self, operation_id: str):
        """
        Reset the parser state for an operation.
        
        Args:
            operation_id: Operation identifier
        """
        if operation_id in self.operation_parsers:
            del self.operation_parsers[operation_id]


class StreamingToolCallParser:
    """
    StreamingToolCallParser - Handles streaming tool call objects with inconsistent chunk formats
    Based on the Qwen Code implementation with modifications for Python.
    
    Problems this parser addresses:
    - Tool calls arrive with varying chunk shapes (empty strings, partial JSON, complete objects)
    - Tool calls may lack IDs, names, or have inconsistent indices
    - Multiple tool calls can be processed simultaneously with interleaved chunks
    - Index collisions occur when the same index is reused for different tool calls
    - JSON arguments are fragmented across multiple chunks and need reconstruction
    """
    
    def __init__(self):
        """Initialize the parser state"""
        # Accumulated buffer containing all received chunks for each tool call index
        self.buffers: Dict[int, str] = {}
        # Current nesting depth in JSON structure for each tool call index
        self.depths: Dict[int, int] = {}
        # Whether we're currently inside a string literal for each tool call index
        self.in_strings: Dict[int, bool] = {}
        # Whether the next character should be treated as escaped for each tool call index
        self.escapes: Dict[int, bool] = {}
        # Metadata for each tool call index
        self.tool_call_meta: Dict[int, Dict[str, Optional[str]]] = {}
        # Map from tool call ID to actual index used for storage
        self.id_to_index_map: Dict[str, int] = {}
        # Counter for generating new indices when collisions occur
        self.next_available_index = 0
    
    def add_chunk(self, index: int, chunk: str, tc_id: Optional[str] = None, name: Optional[str] = None) -> ToolCallParseResult:
        """
        Processes a new chunk of tool call data and attempts to parse complete JSON objects.
        
        Handles the core problems of streaming tool call parsing:
        - Resolves index collisions when the same index is reused for different tool calls
        - Routes chunks without IDs to the correct incomplete tool call
        - Tracks JSON parsing state (depth, string boundaries, escapes) per tool call
        - Attempts parsing only when JSON structure is complete (depth = 0)
        - Repairs common issues like unclosed strings
        
        Args:
            index: Tool call index from streaming response (may collide with existing calls)
            chunk: String chunk that may be empty, partial JSON, or complete data
            tc_id: Optional tool call ID for collision detection and chunk routing
            name: Optional function name stored as metadata
            
        Returns:
            ToolCallParseResult with completion status, parsed value, and repair info
        """
        actual_index = index
        
        # Handle tool call ID mapping for collision detection
        if tc_id:
            # This is the start of a new tool call with an ID
            if tc_id in self.id_to_index_map:
                # We've seen this ID before, use the existing mapped index
                actual_index = self.id_to_index_map[tc_id]
            else:
                # New tool call ID
                # Check if the requested index is already occupied by a different complete tool call
                if index in self.buffers:
                    existing_buffer = self.buffers.get(index, '')
                    existing_depth = self.depths.get(index, 0)
                    existing_meta = self.tool_call_meta.get(index, {})
                    
                    # Check if we have a complete tool call at this index
                    if (
                        existing_buffer.strip() and 
                        existing_depth == 0 and 
                        existing_meta.get('id') and 
                        existing_meta['id'] != tc_id
                    ):
                        try:
                            json.loads(existing_buffer)
                            # We have a complete tool call with a different ID at this index
                            # Find a new index for this tool call
                            actual_index = self._find_next_available_index()
                        except json.JSONDecodeError:
                            # Existing buffer is not complete JSON, we can reuse this index
                            pass
        
                # Map this ID to the actual index we're using
                self.id_to_index_map[tc_id] = actual_index
        else:
            # No ID provided - this is a continuation chunk
            # Try to find which tool call this belongs to based on the index
            # Look for an existing tool call at this index that's not complete
            if index in self.buffers:
                existing_buffer = self.buffers.get(index, '')
                existing_depth = self.depths.get(index, 0)
                
                # If there's an incomplete tool call at this index, continue with it
                if existing_depth > 0 or not existing_buffer.strip():
                    actual_index = index
                else:
                    # Check if the buffer at this index is complete
                    try:
                        json.loads(existing_buffer)
                        # Buffer is complete, this chunk might belong to a different tool call
                        # Find the most recent incomplete tool call
                        actual_index = self._find_most_recent_incomplete_index()
                    except json.JSONDecodeError:
                        # Buffer is incomplete, continue with this index
                        actual_index = index
        
        # Initialize state for the actual index if not exists
        if actual_index not in self.buffers:
            self.buffers[actual_index] = ''
            self.depths[actual_index] = 0
            self.in_strings[actual_index] = False
            self.escapes[actual_index] = False
            self.tool_call_meta[actual_index] = {}
        
        # Update metadata
        meta = self.tool_call_meta.setdefault(actual_index, {})
        if tc_id:
            meta['id'] = tc_id
        if name:
            meta['name'] = name
        
        # Get current state for the actual index
        current_buffer = self.buffers[actual_index]
        current_depth = self.depths[actual_index]
        current_in_string = self.in_strings[actual_index]
        current_escape = self.escapes[actual_index]
        
        # Add chunk to buffer
        new_buffer = current_buffer + chunk
        self.buffers[actual_index] = new_buffer
        
        # Track JSON structure depth - only count brackets/braces outside of strings
        depth = current_depth
        in_string = current_in_string
        escape = current_escape
        
        for char in chunk:
            if not in_string:
                if char in ['{', '[']:
                    depth += 1
                elif char in ['}', ']']:
                    depth -= 1
            
            # Track string boundaries - toggle in_string state on unescaped quotes
            if char == '"' and not escape:
                in_string = not in_string
            # Track escape sequences - backslash followed by any character is escaped
            escape = char == '\\' and not escape
        
        # Update state
        self.depths[actual_index] = depth
        self.in_strings[actual_index] = in_string
        self.escapes[actual_index] = escape
        
        # Attempt parse when we're back at root level (depth 0) and have data
        if depth == 0 and new_buffer.strip():
            try:
                # Standard JSON parsing attempt
                parsed = json.loads(new_buffer)
                return ToolCallParseResult(complete=True, value=parsed)
            except json.JSONDecodeError as e:
                # Intelligent repair: try auto-closing unclosed strings
                if in_string:
                    try:
                        repaired = json.loads(new_buffer + '"')
                        return ToolCallParseResult(
                            complete=True, 
                            value=repaired, 
                            repaired=True
                        )
                    except json.JSONDecodeError:
                        # If repair fails, fall through to error case
                        pass
                return ToolCallParseResult(
                    complete=False, 
                    error=e
                )
        
        # JSON structure is incomplete, continue accumulating chunks
        return ToolCallParseResult(complete=False)
    
    def get_completed_tool_calls(self) -> List[Dict[str, Any]]:
        """
        Gets all completed tool calls that are ready to be emitted.

        Attempts to parse accumulated buffers using multiple strategies:
        1. Standard JSON.parse()
        2. Auto-close unclosed strings and retry
        3. Fallback to safe parsing for malformed data

        Only returns tool calls with both name metadata and non-empty buffers.
        Should be called when streaming is complete (finish_reason is present).

        Returns:
            Array of completed tool calls with their metadata and parsed arguments
        """
        completed = []
        
        for index, buffer in self.buffers.items():
            meta = self.tool_call_meta.get(index, {})
            if meta.get('name') and buffer.strip():
                args = {}
                
                # Try to parse the final buffer
                try:
                    args = json.loads(buffer)
                except json.JSONDecodeError:
                    # Try with repair (auto-close strings)
                    in_string = self.in_strings.get(index, False)
                    if in_string:
                        try:
                            args = json.loads(buffer + '"')
                        except json.JSONDecodeError:
                            # If all parsing fails, return empty args
                            args = {}
                    else:
                        args = {}
                
                completed.append({
                    'id': meta.get('id'),
                    'name': meta.get('name'),
                    'args': args,
                    'index': index
                })
        
        return completed
    
    def get_incomplete_tool_calls(self) -> List[Dict[str, Any]]:
        """
        Gets all incomplete tool calls with their current state.
        
        Returns:
            List of incomplete tool calls with their current state
        """
        incomplete = []
        
        for index, buffer in self.buffers.items():
            depth = self.depths.get(index, 0)
            meta = self.tool_call_meta.get(index, {})
            
            # Only include tool calls that are actually incomplete
            if depth > 0 or not buffer:  # Still in progress or empty
                incomplete.append({
                    'id': meta.get('id'),
                    'name': meta.get('name'),
                    'current_buffer': buffer,
                    'depth': depth,
                    'index': index
                })
        
        return incomplete
    
    def _find_next_available_index(self) -> int:
        """
        Finds the next available index for a new tool call

        Scans indices starting from next_available_index to find one that's safe to use.
        Reuses indices with empty buffers or incomplete parsing states.
        Skips indices with complete, parseable tool call data to prevent overwriting.

        Returns:
            The next available index safe for storing a new tool call
        """
        while self.buffers.get(self.next_available_index) is not None:
            # Check if this index has a complete tool call
            buffer = self.buffers.get(self.next_available_index, '')
            depth = self.depths.get(self.next_available_index, 0)
            meta = self.tool_call_meta.get(self.next_available_index, {})
            
            # If buffer is empty or incomplete (depth > 0), this index is available
            if not buffer.strip() or depth > 0 or not meta.get('id'):
                return self.next_available_index
            
            # Try to parse the buffer to see if it's complete
            try:
                json.loads(buffer)
                # If parsing succeeds and depth is 0, this index has a complete tool call
                if depth == 0:
                    self.next_available_index += 1
                    continue
            except json.JSONDecodeError:
                # If parsing fails, this index is available for reuse
                return self.next_available_index
            
            self.next_available_index += 1
        
        result = self.next_available_index
        self.next_available_index += 1
        return result
    
    def _find_most_recent_incomplete_index(self) -> int:
        """
        Finds the most recent incomplete tool call index

        Used when continuation chunks arrive without IDs. Scans existing tool calls
        to find the highest index with incomplete parsing state (depth > 0, empty buffer,
        or unparseable JSON). Falls back to creating a new index if none found.

        Returns:
            The index of the most recent incomplete tool call, or a new available index
        """
        # Look for the highest index that has an incomplete tool call
        max_index = -1
        for index, buffer in self.buffers.items():
            depth = self.depths.get(index, 0)
            meta = self.tool_call_meta.get(index, {})
            
            # Check if this tool call is incomplete
            if meta.get('id') and (depth > 0 or not buffer.strip()):
                max_index = max(max_index, index)
            elif buffer.strip():
                # Check if buffer is parseable (complete)
                try:
                    json.loads(buffer)
                    # Buffer is complete, skip this index
                except json.JSONDecodeError:
                    # Buffer is incomplete, this could be our target
                    max_index = max(max_index, index)
        
        return max_index if max_index >= 0 else self._find_next_available_index()
    
    def reset(self):
        """
        Resets the entire parser state for processing a new stream

        Clears all accumulated buffers, parsing states, metadata, and counters.
        Allows the parser to be reused for multiple independent streams without
        data leakage between sessions.
        """
        self.buffers.clear()
        self.depths.clear()
        self.in_strings.clear()
        self.escapes.clear()
        self.tool_call_meta.clear()
        self.id_to_index_map.clear()
        self.next_available_index = 0


# Singleton instance for easy access
tool_call_streaming_service = ToolCallStreamingService()