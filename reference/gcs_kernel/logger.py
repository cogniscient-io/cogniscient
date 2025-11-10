"""
Event Logging System implementation for the GCS Kernel.

This module implements the EventLogger class which provides centralized
logging of all kernel operations and tool interactions.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from common.settings import settings


class LogLevel(Enum):
    """Enumeration of log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventLogger:
    """
    Event Logging System that provides centralized logging of all kernel
    operations and tool interactions using structured logging principles.
    """
    
    def __init__(self, log_file: str = "logs/app.log", max_file_size: int = 1024*1024*10, 
                 max_files: int = 5):
        """
        Initialize the event logger.
        
        Args:
            log_file: Path to the log file
            max_file_size: Maximum size of log file before rotation (in bytes)
            max_files: Maximum number of log files to keep
        """
        self.log_file = log_file
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.log_queue = asyncio.Queue()
        self.is_running = False
        self.logger_task = None

    async def initialize(self):
        """Initialize the logger."""
        self.is_running = True
        # Start the logging task
        self.logger_task = asyncio.create_task(self._process_log_queue())

    async def shutdown(self):
        """Shutdown the logger."""
        self.is_running = False
        if self.logger_task:
            self.logger_task.cancel()
            try:
                await self.logger_task
            except asyncio.CancelledError:
                pass

    async def _process_log_queue(self):
        """Process log entries from the queue."""
        while self.is_running:
            try:
                log_entry = await asyncio.wait_for(self.log_queue.get(), timeout=1.0)
                await self._write_log_entry(log_entry)
            except asyncio.TimeoutError:
                continue

    async def _write_log_entry(self, log_entry: Dict[str, Any]):
        """Write a log entry to the log file and potentially to console."""
        # Ensure log directory exists
        import os
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Write the log entry as JSON to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Additionally, output to console for INFO and above levels (matching standard practice)
        level = log_entry.get("level", "INFO")
        message = log_entry.get("message", "")
        timestamp = log_entry.get("timestamp", "")
        
        # Map log levels to numeric values for comparison
        level_values = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        
        # Map log level from settings to numeric value for comparison
        settings_level = settings.log_level.upper()
        settings_level_value = level_values.get(settings_level, 20)  # Default to INFO if invalid

        # Output to console if the message level is at or above the configured log level
        if level_values.get(level, 20) >= settings_level_value:
            print(f"{timestamp} - kernel - {level} - {message}")

    def _create_log_entry(self, level: LogLevel, message: str, 
                         extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a structured log entry."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
            "pid": os.getpid() if 'os' in globals() else "unknown"
        }
        
        if extra_data:
            log_entry.update(extra_data)
        
        return log_entry

    def _log(self, level: LogLevel, message: str, 
             extra_data: Optional[Dict[str, Any]] = None):
        """Internal method to add a log entry to the queue."""
        log_entry = self._create_log_entry(level, message, extra_data)
        try:
            # Non-blocking put if queue has space
            self.log_queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            # If queue is full, log to stderr as fallback
            import sys
            print(f"Log queue full: {log_entry}", file=sys.stderr)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, extra_data)

    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log an info message."""
        self._log(LogLevel.INFO, message, extra_data)

    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, extra_data)

    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log an error message."""
        self._log(LogLevel.ERROR, message, extra_data)

    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log a critical message."""
        self._log(LogLevel.CRITICAL, message, extra_data)

    def log_kernel_event(self, event_type: str, details: Dict[str, Any]):
        """Log a kernel-specific event."""
        extra_data = {
            "event_type": event_type,
            "component": "kernel"
        }
        extra_data.update(details)
        self.info(f"Kernel event: {event_type}", extra_data)

    def log_tool_execution(self, execution_id: str, tool_name: str, 
                          status: str, details: Dict[str, Any]):
        """Log a tool execution event."""
        extra_data = {
            "execution_id": execution_id,
            "tool_name": tool_name,
            "status": status,
            "component": "scheduler"
        }
        extra_data.update(details)
        self.info(f"Tool execution: {tool_name} - {status}", extra_data)

    def log_service_event(self, service_name: str, event_type: str, 
                         details: Dict[str, Any]):
        """Log a service-specific event."""
        extra_data = {
            "service_name": service_name,
            "event_type": event_type,
            "component": "service"
        }
        extra_data.update(details)
        self.info(f"Service event: {service_name} - {event_type}", extra_data)