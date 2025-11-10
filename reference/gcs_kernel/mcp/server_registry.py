"""
MCP Server Registry for managing external MCP server connections.

This module handles storing and retrieving information about connected MCP servers
in the runtime data directory.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    server_id: str
    server_url: str
    name: str
    description: str
    capabilities: List[str]
    last_connected: datetime
    status: str = "active"  # active, disconnected, error


class MCPServerRegistry:
    """Manages the registry of connected MCP servers."""
    
    def __init__(self, runtime_data_directory: str = None, registry_filename: str = None):
        """
        Initialize the registry with a runtime data directory.
        
        Args:
            runtime_data_directory: Directory to store the registry file (default: from global config)
            registry_filename: Name of the registry file (default: from global config)
        """
        # Get the runtime data directory from global settings if not provided
        if runtime_data_directory is None:
            from common.settings import settings
            self.runtime_data_directory = Path(settings.mcp_runtime_data_directory)
        else:
            self.runtime_data_directory = Path(runtime_data_directory)
        
        # Get the registry filename from global settings if not provided
        if registry_filename is None:
            from common.settings import settings
            self.registry_filename = settings.mcp_server_registry_filename
        else:
            self.registry_filename = registry_filename
            
        self.registry_file = self.runtime_data_directory / self.registry_filename
        self._ensure_directory_exists()
        
    def _ensure_directory_exists(self):
        """Ensure the runtime data directory exists."""
        self.runtime_data_directory.mkdir(parents=True, exist_ok=True)
        
    def load_registry(self) -> List[MCPServerInfo]:
        """
        Load the registry of MCP servers from the JSON file.
        
        Returns:
            List of MCPServerInfo objects
        """
        if not self.registry_file.exists():
            return []
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            servers = []
            for server_data in data:
                # Convert timestamp string back to datetime object
                server_data['last_connected'] = datetime.fromisoformat(server_data['last_connected'])
                server_info = MCPServerInfo(**server_data)
                servers.append(server_info)
                
            return servers
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading MCP server registry: {e}")
            return []
    
    def save_registry(self, servers: List[MCPServerInfo]) -> bool:
        """
        Save the registry of MCP servers to the JSON file.
        
        Args:
            servers: List of MCPServerInfo objects to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            server_dicts = []
            for server in servers:
                server_dict = asdict(server)
                # Convert datetime to ISO format string for JSON serialization
                server_dict['last_connected'] = server.last_connected.isoformat()
                server_dicts.append(server_dict)
                
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(server_dicts, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving MCP server registry: {e}")
            return False
    
    def add_server(self, server_info: MCPServerInfo) -> bool:
        """
        Add a server to the registry.
        
        Args:
            server_info: MCPServerInfo object to add
            
        Returns:
            True if successful, False otherwise
        """
        servers = self.load_registry()
        
        # Check if server already exists
        for i, existing_server in enumerate(servers):
            if existing_server.server_id == server_info.server_id:
                # Update existing server
                servers[i] = server_info
                return self.save_registry(servers)
        
        # Add new server
        servers.append(server_info)
        return self.save_registry(servers)
    
    def remove_server(self, server_id: str) -> bool:
        """
        Remove a server from the registry.
        
        Args:
            server_id: ID of the server to remove
            
        Returns:
            True if successful, False otherwise
        """
        servers = self.load_registry()
        servers = [s for s in servers if s.server_id != server_id]
        return self.save_registry(servers)
    
    def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        """
        Get a specific server by ID.
        
        Args:
            server_id: ID of the server to retrieve
            
        Returns:
            MCPServerInfo object if found, None otherwise
        """
        servers = self.load_registry()
        for server in servers:
            if server.server_id == server_id:
                return server
        return None
    
    def get_all_servers(self) -> List[MCPServerInfo]:
        """
        Get all registered servers.
        
        Returns:
            List of all MCPServerInfo objects
        """
        return self.load_registry()
    
    def update_server_status(self, server_id: str, status: str) -> bool:
        """
        Update the status of a server.
        
        Args:
            server_id: ID of the server to update
            status: New status for the server
            
        Returns:
            True if successful, False otherwise
        """
        servers = self.load_registry()
        updated = False
        
        for server in servers:
            if server.server_id == server_id:
                server.status = status
                server.last_connected = datetime.now()
                updated = True
        
        if updated:
            return self.save_registry(servers)
        
        return updated

    def list_server_ids(self) -> List[str]:
        """
        Get a list of all known server IDs.
        
        Returns:
            List of server IDs
        """
        servers = self.load_registry()
        return [server.server_id for server in servers]
    
    def list_server_info(self) -> List[MCPServerInfo]:
        """
        Get detailed information about all known servers.
        
        Returns:
            List of MCPServerInfo objects
        """
        return self.load_registry()
    
    def server_exists(self, server_id: str) -> bool:
        """
        Check if a server exists in the registry.
        
        Args:
            server_id: ID of the server to check
            
        Returns:
            True if the server exists, False otherwise
        """
        servers = self.load_registry()
        for server in servers:
            if server.server_id == server_id:
                return True
        return False