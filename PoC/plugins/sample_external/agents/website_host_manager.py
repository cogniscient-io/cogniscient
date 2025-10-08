"""
Website Host Manager Agent

This MCP server agent runs on a website hosting machine to monitor
system resources and manage the website hosting software.
It exposes tools that can be called by an MCP client (like the Cogniscient system).

This version directly uses FastMCP without the wrapper to ensure proper schema generation.
"""

import psutil
from typing import Dict, Any, List
from enum import Enum
import asyncio
import sys
import json

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context


class SystemMetrics(Enum):
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    PROCESS_STATUS = "process_status"


class WebsiteHostManagerAgent:
    """
    An MCP server that exposes tools to an MCP client.
    This implementation directly uses FastMCP decorators for proper schema generation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {
                "hosted_software_process_name": "nginx",
                "restart_threshold": 60
            }
        
        # Create the MCP server instance
        self.mcp = FastMCP(
            name="WebsiteHostManager",
            instructions="Use this agent to monitor system resources (CPU, memory, network, disk) and manage website hosting software (check status, restart if hung)"
        )
        
        self.hosted_software_process_name = config.get("hosted_software_process_name", "nginx")
        self.restart_threshold = config.get("restart_threshold", 60)  # seconds without response
        
        # Register the tools this agent supports via MCP using direct decorators
        # This allows FastMCP to properly generate schemas based on function signatures
        
        # Register get_system_metrics with proper function signature and schema
        @self.mcp.tool(
            name="get_system_metrics",
            description="Retrieves current system metrics (CPU, memory, network, disk usage)",
        )
        async def get_system_metrics(ctx: Context, metrics: List[str]) -> Dict[str, Any]:
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
                result[SystemMetrics.PROCESS_STATUS.value] = self._check_process_status(ctx)
                
            await ctx.info(f"Retrieved system metrics: {list(result.keys())}")
            return result

        # Register check_hosted_software_status with proper function signature
        @self.mcp.tool(
            name="check_hosted_software_status", 
            description="Checks if the hosted software is running properly",
        )
        async def check_hosted_software_status(ctx: Context) -> Dict[str, Any]:
            """Check if the hosted software is running properly."""
            process_status = self._check_process_status(ctx)
            
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

        # Register restart_hosted_software with proper function signature
        @self.mcp.tool(
            name="restart_hosted_software",
            description="Restarts the hosted software if it's hung or not responding",
        )
        async def restart_hosted_software(ctx: Context) -> Dict[str, Any]:
            """Restart the hosted software if it's hung or not responding."""
            # First, try to gracefully stop the process
            process_status = self._check_process_status(ctx)
            
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

    def _check_process_status(self, ctx: Context) -> Dict[str, Any]:
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

    def run(self, transport: str = "stdio"):
        """
        Run the MCP external agent server synchronously.

        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
        """
        print(f"Starting MCP external agent WebsiteHostManager with {transport} transport")
        self.mcp.run(transport=transport)

    def run_http_server(self, host: str = "127.0.0.1", port: int = 9100):
        """
        Run the MCP external agent as an HTTP server using streamable HTTP transport.

        Args:
            host: Host address for the HTTP server (default: 127.0.0.1)
            port: Port for the HTTP server (default: 9100)
        """
        import asyncio
        print(f"Starting MCP external agent HTTP server WebsiteHostManager on {host}:{port}")
        # Update the MCP server settings for HTTP
        self.mcp.settings.host = host
        self.mcp.settings.port = port
        # Use asyncio to run the HTTP server
        asyncio.run(self.mcp.run_streamable_http_async())


# Example usage with HTTP server support
if __name__ == "__main__":
    import json
    import sys
    
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
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "http":
            port = 9100  # default port
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                    print(f"Starting agent as HTTP server on http://127.0.0.1:{port}/mcp")
                except ValueError:
                    print(f"Invalid port: {sys.argv[2]}. Using default port 9100.")
                    port = 9100
            else:
                print(f"Starting agent as HTTP server on http://127.0.0.1:{port}/mcp")
            
            agent.run_http_server(host="127.0.0.1", port=port)
        elif sys.argv[1] == "sse":
            port = 9100  # default port
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                    print(f"Starting agent as SSE server on http://127.0.0.1:{port}")
                except ValueError:
                    print(f"Invalid port: {sys.argv[2]}. Using default port 9100.")
                    port = 9100
            else:
                print(f"Starting agent as SSE server on http://127.0.0.1:{port}")
            
            agent.run_http_server(host="127.0.0.1", port=port)  # Use HTTP server functionality for SSE as well
        elif sys.argv[1] == "stdio":
            print("Starting agent with stdio transport")
            agent.run(transport="stdio")
        else:
            print(f"Unknown transport: {sys.argv[1]}")
            print("Usage: python website_host_manager.py [http|sse|stdio] [port]")
    else:
        # Default to stdio transport for backward compatibility
        print("Starting agent with stdio transport (default)")
        agent.run(transport="stdio")