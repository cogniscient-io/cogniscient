"""MCP Connection Registry - Persistent storage and management of successful MCP server connections."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime
import os


class MCPConnectionData:
    """Represents data for an MCP connection that can be stored in the registry."""
    
    def __init__(
        self, 
        agent_id: str, 
        connection_params: Dict[str, Any], 
        timestamp: Optional[datetime] = None,
        status: str = "connected",
        last_validated: Optional[datetime] = None
    ):
        self.agent_id = agent_id
        self.connection_params = connection_params
        self.timestamp = timestamp or datetime.now()
        self.status = status
        self.last_validated = last_validated or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection data to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "connection_params": self.connection_params,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPConnectionData':
        """Create connection data from dictionary."""
        from datetime import datetime
        timestamp = datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
        last_validated = datetime.fromisoformat(data["last_validated"]) if data.get("last_validated") else None
        return cls(
            agent_id=data["agent_id"],
            connection_params=data["connection_params"],
            timestamp=timestamp,
            status=data.get("status", "connected"),
            last_validated=last_validated
        )


class MCPConnectionRegistry:
    """Handles registration, storage, and management of MCP connections to external servers."""
    
    def __init__(self, registry_file: Optional[str] = None, runtime_data_dir: Optional[str] = None):
        """Initialize the MCP connection registry.
        
        Args:
            registry_file: Path to the file where MCP connection data is stored
            runtime_data_dir: Directory where runtime data files are stored
        """
        from cogniscient.engine.config.settings import settings
        
        # Determine the runtime data directory
        if runtime_data_dir is None:
            # Use the settings directory if available
            runtime_data_dir = getattr(settings, 'runtime_data_dir', 'runtime_data')
        
        # Ensure the runtime data directory exists
        os.makedirs(runtime_data_dir, exist_ok=True)
        
        # If no specific registry file provided, use default in runtime data dir
        if registry_file is None:
            self.registry_file = os.path.join(runtime_data_dir, "external_agents_registry.json")
        else:
            self.registry_file = registry_file
        
        self.connections: Dict[str, MCPConnectionData] = {}
        
        # Load existing connection data from file
        self.load_registry()
    
    def save_connection(self, connection_data: MCPConnectionData) -> bool:
        """Save an MCP connection to the registry.
        
        Args:
            connection_data: The connection data to save
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            self.connections[connection_data.agent_id] = connection_data
            self.save_registry()
            print(f"Successfully saved connection to registry for agent: {connection_data.agent_id}")
            return True
        except Exception as e:
            print(f"Failed to save connection to registry for agent {connection_data.agent_id}: {e}")
            return False
    
    def get_connection(self, agent_id: str) -> Optional[MCPConnectionData]:
        """Get an MCP connection by agent ID.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            The connection data or None if not found
        """
        return self.connections.get(agent_id)
    
    def remove_connection(self, agent_id: str) -> bool:
        """Remove an MCP connection from the registry.
        
        Args:
            agent_id: ID of the agent to remove
            
        Returns:
            bool: True if removal was successful, False otherwise
        """
        if agent_id not in self.connections:
            print(f"Connection for agent {agent_id} not found in registry")
            return False
        
        try:
            del self.connections[agent_id]
            self.save_registry()
            print(f"Successfully removed connection from registry for agent: {agent_id}")
            return True
        except Exception as e:
            print(f"Failed to remove connection from registry for agent {agent_id}: {e}")
            return False
    
    def is_connection_valid(self, agent_id: str, connection_params: Dict[str, Any]) -> bool:
        """Check if a connection is still valid.
        
        Args:
            agent_id: ID of the agent
            connection_params: The connection parameters to validate against
            
        Returns:
            bool: True if connection is valid, False otherwise
        """
        connection_data = self.get_connection(agent_id)
        if not connection_data:
            return False
        
        # Check if the connection parameters match
        if connection_data.connection_params != connection_params:
            return False
        
        # Check if the connection status is good
        if connection_data.status != "connected":
            return False
        
        # For this initial implementation, we assume connections are valid if they
        # exist and match the parameters. In a more advanced implementation, we
        # might want to perform actual connection validation here.
        return True
    
    def update_connection_timestamp(self, agent_id: str) -> bool:
        """Update the timestamp of a connection to now.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        connection_data = self.get_connection(agent_id)
        if not connection_data:
            print(f"Connection for agent {agent_id} not found in registry")
            return False
        
        try:
            connection_data.last_validated = datetime.now()
            self.save_registry()
            return True
        except Exception as e:
            print(f"Failed to update timestamp for agent {agent_id}: {e}")
            return False
    
    def save_registry(self):
        """Save the current registry to the registry file."""
        try:
            # Prepare data for serialization
            serializable_data = {}
            for agent_id, connection_data in self.connections.items():
                serializable_data[agent_id] = connection_data.to_dict()
            
            # Write to registry file
            with open(self.registry_file, "w") as f:
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save registry to {self.registry_file}: {e}")
    
    def load_registry(self):
        """Load the registry from the registry file."""
        registry_path = Path(self.registry_file)
        if not registry_path.exists():
            # Create an empty registry file if it doesn't exist
            with open(self.registry_file, "w") as f:
                json.dump({}, f)
            return
        
        try:
            with open(self.registry_file, "r") as f:
                raw_data = json.load(f)
            
            # Convert loaded data back to MCPConnectionData objects
            self.connections = {}
            for agent_id, connection_dict in raw_data.items():
                try:
                    connection_data = MCPConnectionData.from_dict(connection_dict)
                    self.connections[agent_id] = connection_data
                except Exception as e:
                    print(f"Failed to reconstruct connection for agent {agent_id}: {e}")
        except Exception as e:
            print(f"Failed to load registry from {self.registry_file}: {e}")
    
    def get_all_connections(self) -> Dict[str, MCPConnectionData]:
        """Get all connections in the registry.
        
        Returns:
            Dict mapping agent IDs to connection data
        """
        return self.connections.copy()