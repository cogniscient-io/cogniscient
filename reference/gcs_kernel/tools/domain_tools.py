"""
Domain tools for the GCS Kernel.

This module implements tools for managing and interacting with domains.
"""

from typing import Dict, Any
from gcs_kernel.registry import BaseTool
from gcs_kernel.models import ToolResult


class DomainListTool:
    """
    System tool to list all available domains.
    """
    name = "domain_list"
    display_name = "List Domains"
    description = "List all available domains with their descriptions and status"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the domain list tool.

        Args:
            parameters: The parameters for tool execution (none required)

        Returns:
            A ToolResult containing the execution result
        """
        try:
            if not self.kernel or not hasattr(self.kernel, 'domain_manager') or self.kernel.domain_manager is None:
                result = "Domain manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=result,
                    llm_content=result,
                    return_display=result
                )

            # Get available domains from the domain manager
            domains = self.kernel.domain_manager.get_available_domains()

            if not domains:
                result = "No domains are currently available."
            else:
                domain_list = []
                for name, description in domains.items():
                    # Check if this domain is currently loaded
                    current_domain = getattr(self.kernel.domain_manager, 'current_domain', None)
                    status = "LOADED" if name == current_domain else "AVAILABLE"
                    domain_list.append(f"  - {name} ({status}): {description}")

                result = "Available domains:\n" + "\n".join(sorted(domain_list))

            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error listing domains: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class DomainLoadTool:
    """
    System tool to load a domain by name.
    """
    name = "domain_load"
    display_name = "Load Domain"
    description = "Load a domain by its name, unloading the current domain if one is loaded"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "domain_name": {
                "type": "string",
                "description": "The name of the domain to load"
            }
        },
        "required": ["domain_name"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the domain load tool.

        Args:
            parameters: The parameters for tool execution

        Returns:
            A ToolResult containing the execution result
        """
        domain_name = parameters.get("domain_name")

        if not domain_name:
            error_msg = "Missing required parameter: domain_name"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )

        try:
            if not self.kernel or not hasattr(self.kernel, 'domain_manager') or self.kernel.domain_manager is None:
                error_msg = "Domain manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Check if domain exists
            available_domains = self.kernel.domain_manager.get_available_domains()
            if domain_name not in available_domains:
                error_msg = f"Domain '{domain_name}' does not exist. Available domains: {', '.join(available_domains.keys())}"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Load the domain
            success = await self.kernel.domain_manager.load_domain(domain_name)

            if success:
                result = f"Successfully loaded domain '{domain_name}'. Tools and configurations from this domain are now active."
            else:
                error_msg = f"Failed to load domain '{domain_name}'. Check domain validity and structure."
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error loading domain '{domain_name}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class DomainUnloadTool:
    """
    System tool to unload the currently loaded domain.
    """
    name = "domain_unload"
    display_name = "Unload Domain"
    description = "Unload the currently loaded domain, reverting to default tools and configurations"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {},
        "required": []
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the domain unload tool.

        Args:
            parameters: The parameters for tool execution (none required)

        Returns:
            A ToolResult containing the execution result
        """
        try:
            if not self.kernel or not hasattr(self.kernel, 'domain_manager') or self.kernel.domain_manager is None:
                error_msg = "Domain manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Check if any domain is currently loaded
            current_domain = getattr(self.kernel.domain_manager, 'current_domain', None)
            if not current_domain:
                result = "No domain is currently loaded to unload."
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    llm_content=result,
                    return_display=result
                )

            # Unload the current domain
            success = await self.kernel.domain_manager.unload_domain()

            if success:
                result = f"Successfully unloaded domain '{current_domain}'. Reverted to default tools and configurations."
            else:
                error_msg = f"Failed to unload domain '{current_domain}'."
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error unloading domain: {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


class DomainInfoTool:
    """
    System tool to get information about a specific domain.
    """
    name = "domain_info"
    display_name = "Get Domain Info"
    description = "Get detailed information about a specific domain including its metadata"
    parameters = {  # Following OpenAI-compatible format
        "type": "object",
        "properties": {
            "domain_name": {
                "type": "string",
                "description": "The name of the domain to get information for"
            }
        },
        "required": ["domain_name"]
    }

    def __init__(self, kernel):
        """
        Initialize the tool with a reference to the kernel.

        Args:
            kernel: The GCSKernel instance
        """
        self.kernel = kernel

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        Execute the domain info tool.

        Args:
            parameters: The parameters for tool execution

        Returns:
            A ToolResult containing the execution result
        """
        domain_name = parameters.get("domain_name")

        if not domain_name:
            error_msg = "Missing required parameter: domain_name"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )

        try:
            if not self.kernel or not hasattr(self.kernel, 'domain_manager') or self.kernel.domain_manager is None:
                error_msg = "Domain manager not available"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Check if domain exists
            available_domains = self.kernel.domain_manager.available_domains
            if domain_name not in available_domains:
                error_msg = f"Domain '{domain_name}' does not exist. Available domains: {', '.join(available_domains.keys())}"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            # Read domain metadata
            domain_path = available_domains[domain_name]
            metadata_path = domain_path / "metadata.json"

            import json
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                # Get additional info about whether domain is currently loaded
                current_domain = getattr(self.kernel.domain_manager, 'current_domain', None)
                is_loaded = domain_name == current_domain
                loaded_status = "LOADED" if is_loaded else "AVAILABLE"

                result = f"Domain Information for '{domain_name}' ({loaded_status}):\n"
                result += f"  Name: {metadata.get('name', 'N/A')}\n"
                result += f"  Description: {metadata.get('description', 'N/A')}\n"
                result += f"  Version: {metadata.get('version', 'N/A')}\n"
                result += f"  Author: {metadata.get('author', 'N/A')}\n"
                result += f"  Path: {str(domain_path)}\n"

                # Check for additional domain components
                has_prompts = (domain_path / "prompts.json").exists()
                has_tools = (domain_path / "tools.json").exists() or (domain_path / "tools").exists()
                has_mcp_servers = (domain_path / "mcp_servers.json").exists() or (domain_path / "mcp_servers").exists()

                result += f"  Has Prompts: {'Yes' if has_prompts else 'No'}\n"
                result += f"  Has Tools: {'Yes' if has_tools else 'No'}\n"
                result += f"  Has MCP Servers: {'Yes' if has_mcp_servers else 'No'}\n"

            except (json.JSONDecodeError, FileNotFoundError):
                error_msg = f"Could not read metadata for domain '{domain_name}'"
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    error=error_msg,
                    llm_content=error_msg,
                    return_display=error_msg
                )

            return ToolResult(
                tool_name=self.name,
                success=True,
                llm_content=result,
                return_display=result
            )
        except Exception as e:
            error_msg = f"Error getting domain info for '{domain_name}': {str(e)}"
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_msg,
                llm_content=error_msg,
                return_display=error_msg
            )


# List of all domain tools to register
DOMAIN_TOOLS = [
    DomainListTool,
    DomainLoadTool,
    DomainUnloadTool,
    DomainInfoTool
]


async def register_domain_tools(kernel) -> bool:
    """
    Register all domain-related tools with the kernel registry.
    This should be called after the kernel and registry are initialized.

    Args:
        kernel: The GCSKernel instance

    Returns:
        True if registration was successful, False otherwise
    """
    import time
    start_time = time.time()

    from gcs_kernel.registry import ToolRegistry

    # Check if the kernel and registry are available
    if not kernel or not hasattr(kernel, 'registry') or kernel.registry is None:
        if hasattr(kernel, 'logger') and kernel.logger:
            try:
                kernel.logger.error("Kernel registry not available for domain tool registration")
            except TypeError:
                # Handle case where logger is a MagicMock
                if hasattr(kernel.logger, '_mock_name'):
                    kernel.logger.error("Kernel registry not available for domain tool registration")
                else:
                    raise
        return False

    registry = kernel.registry

    if hasattr(kernel, 'logger') and kernel.logger:
        try:
            kernel.logger.debug("Starting domain tools registration...")
        except TypeError:
            # Handle case where logger is a MagicMock
            if hasattr(kernel.logger, '_mock_name'):
                kernel.logger.debug("Starting domain tools registration...")
            else:
                raise

    # List of domain tools to register
    domain_tools = [
        DomainListTool(kernel),
        DomainLoadTool(kernel),
        DomainUnloadTool(kernel),
        DomainInfoTool(kernel)
    ]

    # Register each domain tool
    for tool in domain_tools:
        if hasattr(kernel, 'logger') and kernel.logger:
            try:
                kernel.logger.debug(f"Registering domain tool: {tool.name}")
            except TypeError:
                # Handle case where logger is a MagicMock
                if hasattr(kernel.logger, '_mock_name'):
                    kernel.logger.debug(f"Registering domain tool: {tool.name}")
                else:
                    raise

        success = await registry.register_tool(tool)
        if not success:
            if hasattr(kernel, 'logger') and kernel.logger:
                try:
                    kernel.logger.error(f"Failed to register domain tool: {tool.name}")
                except TypeError:
                    # Handle case where logger is a MagicMock
                    if hasattr(kernel.logger, '_mock_name'):
                        kernel.logger.error(f"Failed to register domain tool: {tool.name}")
                    else:
                        raise
            return False

    elapsed = time.time() - start_time
    if hasattr(kernel, 'logger') and kernel.logger:
        try:
            kernel.logger.info(f"Successfully registered {len(domain_tools)} domain tools (elapsed: {elapsed:.2f}s)")
        except TypeError:
            # Handle case where logger is a MagicMock
            if hasattr(kernel.logger, '_mock_name'):
                kernel.logger.info(f"Successfully registered {len(domain_tools)} domain tools (elapsed: {elapsed:.2f}s)")
            else:
                raise

    return True