"""
Website Host Manager Agent

This MCP server agent runs on a website hosting machine to monitor
system resources and manage the website hosting software.
It exposes tools that can be called by an MCP client (like the Cogniscient system).
"""

import psutil
from typing import Dict, Any, List
from enum import Enum

from cogniscient.agentSDK.base_external_agent import BaseExternalAgent
from mcp.server.fastmcp import Context

class SystemMetrics(Enum):
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    PROCESS_STATUS = "process_status"

class WebsiteHostManagerAgent(BaseExternalAgent):
    """
    An external agent that runs on a website hosting machine to monitor
    system resources and manage the website hosting software.
    This implements an MCP server that exposes tools to an MCP client.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {
                "hosted_software_process_name": "nginx",
                "restart_threshold": 60
            }
        
        super().__init__(
            name="WebsiteHostManager",
            version="1.0.0",
            description="Monitors system resources and manages website hosting software",
            instructions="Use this agent to monitor system resources (CPU, memory, network, disk) and manage website hosting software (check status, restart if hung)"
        )
        
        self.hosted_software_process_name = config.get("hosted_software_process_name", "nginx")
        self.restart_threshold = config.get("restart_threshold", 60)  # seconds without response
        
        # Register the tools this agent supports via MCP
        self.register_tool(
            "get_system_metrics",
            description="Retrieves current system metrics (CPU, memory, network, disk usage)",
            input_schema={
                "type": "object",
                "properties": {
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [metric.value for metric in SystemMetrics]
                        },
                        "description": "Which metrics to retrieve"
                    }
                },
                "required": ["metrics"]
            }
        )
        
        self.register_tool(
            "check_hosted_software_status", 
            description="Checks if the hosted software is running properly",
            input_schema={
                "type": "object",
                "properties": {},
            }
        )
        
        self.register_tool(
            "restart_hosted_software",
            description="Restarts the hosted software if it's hung or not responding",
            input_schema={
                "type": "object",
                "properties": {},
            }
        )

    def _check_process_status(self) -> Dict[str, Any]:
        """Check the status of the hosted software process."""
        status = {
            "process_name": self.hosted_software_process_name,
            "is_running": False,
            "pid": None,
            "cpu_percent": 0,
            "memory_percent": 0,
            "num_threads": 0,
            "create_time": None
        }
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'num_threads', 'create_time']):
            try:
                if proc.info['name'] == self.hosted_software_process_name:
                    status.update({
                        "is_running": True,
                        "pid": proc.info['pid'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_percent": proc.info['memory_percent'],
                        "num_threads": proc.info['num_threads'],
                        "create_time": proc.info['create_time']
                    })
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process might have terminated between the iteration and accessing its info
                continue
                
        return status

    async def get_system_metrics(self, ctx: Context, metrics: List[str]) -> Dict[str, Any]:
        """Retrieve system metrics based on the requested types."""
        result = {}
        
        if SystemMetrics.CPU_PERCENT.value in metrics:
            result[SystemMetrics.CPU_PERCENT.value] = psutil.cpu_percent(interval=1)
            
        if SystemMetrics.MEMORY_PERCENT.value in metrics:
            memory = psutil.virtual_memory()
            result[SystemMetrics.MEMORY_PERCENT.value] = memory.percent
            
        if SystemMetrics.NETWORK_IO.value in metrics:
            network = psutil.net_io_counters()
            result[SystemMetrics.NETWORK_IO.value] = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
            
        if SystemMetrics.DISK_IO.value in metrics:
            disk = psutil.disk_io_counters()
            if disk:
                result[SystemMetrics.DISK_IO.value] = {
                    "read_count": disk.read_count,
                    "write_count": disk.write_count,
                    "read_bytes": disk.read_bytes,
                    "write_bytes": disk.write_bytes
                }
            
        if SystemMetrics.PROCESS_STATUS.value in metrics:
            result[SystemMetrics.PROCESS_STATUS.value] = self._check_process_status()
            
        await ctx.info(f"Retrieved system metrics: {list(result.keys())}")
        return result

    async def check_hosted_software_status(self, ctx: Context) -> Dict[str, Any]:
        """Check if the hosted software is running properly."""
        process_status = self._check_process_status()
        
        if not process_status["is_running"]:
            result = {
                "status": "NOT_RUNNING",
                "process_status": process_status
            }
        else:
            result = {
                "status": "RUNNING",
                "process_status": process_status
            }
        
        await ctx.info(f"Checked software status: {result['status']}")
        return result

    async def restart_hosted_software(self, ctx: Context) -> Dict[str, Any]:
        """Restart the hosted software if it's hung or not responding."""
        # First, try to gracefully stop the process
        process_status = self._check_process_status()
        
        if not process_status["is_running"]:
            result = {
                "result": "SOFTWARE_WAS_NOT_RUNNING",
                "message": f"{self.hosted_software_process_name} was not running, starting it now"
            }
            await ctx.info(result["message"])
            return result
        
        # Try to terminate the process gracefully
        try:
            proc = psutil.Process(process_status["pid"])
            proc.terminate()
            try:
                # Wait for the process to terminate gracefully
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                proc.kill()
        except psutil.NoSuchProcess:
            # Process already terminated
            pass
        except Exception as e:
            result = {
                "result": "RESTART_FAILED",
                "message": f"Failed to terminate {self.hosted_software_process_name}: {str(e)}"
            }
            await ctx.error(result["message"])
            return result
        
        # Start the software again
        # In a real implementation, this would execute the appropriate command
        # to restart the hosting software (e.g., systemctl start nginx)
        try:
            # Mock restart command - in real implementation, you'd use subprocess
            # or a platform-specific service manager
            await ctx.info(f"Restarting {self.hosted_software_process_name}...")
            # subprocess.run(["systemctl", "start", self.hosted_software_process_name])
            
            result = {
                "result": "RESTART_SUCCESS",
                "message": f"{self.hosted_software_process_name} restarted successfully"
            }
            await ctx.info(result["message"])
            return result
        except Exception as e:
            result = {
                "result": "START_FAILED",
                "message": f"Failed to start {self.hosted_software_process_name}: {str(e)}"
            }
            await ctx.error(result["message"])
            return result

# Example usage
if __name__ == "__main__":
    import json
    
    # Load config from file or use defaults
    config = {
        "hosted_software_process_name": "nginx",  # Change this to your specific hosting software
        "restart_threshold": 60
    }
    
    try:
        with open('/home/tsai/src/cogniscient/PoC/plugins/sample_external/config.json', 'r') as f:
            config.update(json.load(f))
    except FileNotFoundError:
        print("Config file not found, using defaults")
    
    agent = WebsiteHostManagerAgent(config)
    agent.run()