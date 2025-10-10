"""Kernel implementation following the ringed architecture design."""

import asyncio
import threading
from typing import Dict, Optional
from cogniscient.engine.services.service_interface import Service


class Kernel:
    """Kernel class that follows the ringed architecture design."""
    
    def __init__(self):
        """Initialize the kernel with minimal public interface."""
        self.service_registry: Dict[str, Service] = {}
        self._initialized = False
        
    async def initialize(self):
        """Initialize the kernel and registered services."""
        # Initialize kernel first, then services
        # Ensure services are initialized in proper dependency order
        for service in self.service_registry.values():
            await service.initialize()
        self._initialized = True
        
    async def shutdown(self):
        """Shutdown the kernel and registered services in reverse order."""
        # Shutdown in reverse initialization order
        for service in reversed(list(self.service_registry.values())):
            await service.shutdown()
    
    def register_service(self, name: str, service: Service) -> bool:
        """Register a service with the kernel.
        
        Args:
            name: Name of the service to register
            service: Service instance to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        if name in self.service_registry:
            return False
        self.service_registry[name] = service
        return True
        
    def get_service(self, name: str) -> Optional[Service]:
        """Get a service by name.
        
        Args:
            name: Name of the service to retrieve
            
        Returns:
            Service instance if found, None otherwise
        """
        return self.service_registry.get(name)
        
    # System lifecycle management methods
    def start_system(self):
        """Start system kernel loop - kernel-only responsibility."""
        print("Kernel started - All system management delegated to kernel")
        # Start the main kernel control loop in a separate thread
        import threading
        import asyncio
        
        # Create an event loop for the kernel
        self.kernel_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.kernel_loop)
        
        # Start the control loop in the new event loop
        self.kernel_thread = threading.Thread(target=self._run_kernel_loop, args=(self.kernel_loop,))
        self.kernel_thread.start()
        
        return True
    
    def _run_kernel_loop(self, loop):
        """Internal method to run the kernel control loop."""
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._control_loop())
        except RuntimeError as e:
            # Handle the specific case where event loop is stopped before Future completes
            # This happens during shutdown when loop.stop() is called while run_until_complete is waiting
            if "Event loop stopped before Future completed" not in str(e):
                # Only re-raise if it's not the expected shutdown error
                raise
    
    async def _control_loop(self):
        """Main control loop for the kernel."""
        print("Kernel control loop started...")
        self._running = True
        
        # Initialize all services
        await self.initialize()
        
        while self._running:
            # Process any pending kernel tasks
            await self._process_kernel_tasks()
            
            # Yield control briefly to allow other coroutines to run
            # Use a short sleep that can be interrupted by cancellation
            try:
                # Sleep in small intervals to allow quick response to stop signal
                for _ in range(10):  # Check 10 times within the 10ms period
                    if not self._running:
                        return  # Exit the coroutine early if _running is False
                    await asyncio.sleep(0.001)  # 1ms delay instead of 10ms
            except asyncio.CancelledError:
                # If the task is cancelled (which can happen during shutdown), exit gracefully
                break
    
    async def _process_kernel_tasks(self):
        """Process kernel-level tasks."""
        # In a real implementation, this would handle system-level tasks
        # For now, just a placeholder
        pass
    
    def stop_system(self):
        """Stop system kernel loop - kernel-only responsibility."""
        print("Stopping kernel...")
        self._running = False
        
        # Close the event loop
        if hasattr(self, 'kernel_loop') and self.kernel_loop:
            self.kernel_loop.call_soon_threadsafe(self.kernel_loop.stop)
        
        # Wait for the thread to finish
        if hasattr(self, 'kernel_thread') and self.kernel_thread:
            self.kernel_thread.join()
        
        print("Kernel stopped")
        return True
    
    def set_input_handler(self, handler):
        """Set the input handler for the kernel."""
        self.input_handler = handler
    
    def set_output_handler(self, handler):
        """Set the output handler for the kernel."""
        self.output_handler = handler
    
    def process_input(self, input_data):
        """Process input through the kernel."""
        if hasattr(self, 'input_handler') and self.input_handler:
            return self.input_handler(input_data)
        else:
            return "No input handler registered with kernel."
    
    def send_output(self, output_data):
        """Send output through the kernel."""
        if hasattr(self, 'output_handler') and self.output_handler:
            return self.output_handler(output_data)
        else:
            print(output_data)  # fallback to standard output
        
    # Resource coordination methods
    def allocate_resource(self, resource_type: str, amount: int):
        """Allocate system resources - kernel-only responsibility."""
        # In a real implementation, this would manage memory, CPU, etc.
        print(f"Allocating {amount} units of {resource_type}")
        return True
        
    # Security boundary methods
    def validate_access(self, service: str, action: str, context: Dict) -> bool:
        """Validate access to services - kernel-only responsibility."""
        # In a real implementation, this would check permissions
        print(f"Validating access to {service} for action {action}")
        return True