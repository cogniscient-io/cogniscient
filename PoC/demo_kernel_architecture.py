#!/usr/bin/env python3
"""
Demo script to showcase the new kernel-based architecture where LLM interactions
are handled in the kernel control loop, and UIs act as I/O channels.
"""

import asyncio
from cogniscient.engine.gcs_runtime import GCSRuntime
from cogniscient.engine.llm_orchestrator.llm_orchestrator import LLMOrchestrator
from cogniscient.engine.llm_orchestrator.chat_interface import ChatInterface
from cogniscient.engine.config.settings import settings


def demo_callback(event_type: str, content: str = None, data: dict = None):
    """Demo callback to handle streaming events from the kernel."""
    print(f"🔄 KERNEL EVENT: {event_type}")
    if content:
        print(f"📝 Content: {content}")
    if data:
        print(f"📊 Data: {data}")
    print("-" * 50)


async def main():
    """Main function to demonstrate the new kernel-based architecture."""
    print("🚀 Starting Demo: Kernel-Based Architecture with LLM Interactions")
    print("=" * 60)
    
    # Initialize the GCS Runtime
    print("🔧 Initializing GCS Runtime...")
    gcs_runtime = GCSRuntime(config_dir=settings.config_dir, agents_dir=settings.agents_dir)
    
    # Load all agents - using the GCS Runtime method
    print("📦 Loading agents...")
    await gcs_runtime.load_all_agents()
    
    # Initialize orchestrator and chat interface
    print("🤖 Initializing LLM orchestrator and chat interface...")
    orchestrator = LLMOrchestrator(gcs_runtime)
    chat_interface = ChatInterface(orchestrator)
    
    # Register with the kernel
    print("🔗 Registering orchestrator and chat interface with kernel...")
    gcs_runtime.set_llm_orchestrator(orchestrator)
    gcs_runtime.register_chat_interface(chat_interface)
    
    # Start the kernel system
    print("🖥️  Starting kernel control loop...")
    gcs_runtime.start_kernel_loop()
    
    # Add a demo callback to see streaming events
    gcs_runtime.kernel.add_streaming_callback(demo_callback)
    
    print("\n🎯 Kernel-based architecture is now ready!")
    print("   - LLM interactions happen in the kernel control loop")
    print("   - UIs act as I/O channels only")
    print("   - Conversation history is managed centrally in the kernel")
    
    # Process a sample user input through the kernel
    print("\n💬 Processing sample user input via kernel...")
    sample_input = "What can you do to help me with my system?"
    
    result = await gcs_runtime.kernel.process_user_input_streaming(sample_input)
    print(f"\n✅ Response from kernel: {result}")
    
    # Show that conversation history is maintained in the kernel
    print("\n📋 Conversation history in kernel:")
    for idx, entry in enumerate(gcs_runtime.kernel.get_conversation_history()):
        print(f"   {idx+1}. {entry['role'].upper()}: {entry['content'][:50]}...")
    
    print("\n✅ Demo completed successfully!")
    
    # Shutdown the system
    print("\n🛑 Shutting down the system...")
    await gcs_runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())