# Turn Manager Tests

This directory contains comprehensive tests for the TurnManager component of the AI Orchestrator in the GCS Kernel.

## Overview

The TurnManager handles turn-based AI interactions, managing the flow between streaming content and tool execution. These tests cover:

- Basic initialization and setup
- Conversation history management
- Turn execution with and without tool calls
- Tool call execution and response handling
- Error handling and edge cases
- Recursive tool call scenarios
- Cancellation and timeout handling

## Test Organization

- `test_turn_manager.py`: Core functionality tests for the TurnManager class
- `test_turn_event.py`: Tests for the TurnEvent class
- `test_turn_event_type.py`: Tests for the TurnEventType enum
- `test_turn_manager_edge_cases.py`: Edge case scenarios and internal method tests
- `conftest.py`: Shared test fixtures and configurations

## Running Tests

To run all turn manager tests:

```bash
python3 -m pytest tests/turn_manager/
```

To run with verbose output:

```bash
python3 -m pytest tests/turn_manager/ -v
```

To run a specific test file:

```bash
python3 -m pytest tests/turn_manager/test_turn_manager.py
```

## Test Coverage

The tests include:

- Happy path scenarios for content generation
- Tool call request and response handling
- Error scenarios and edge cases
- Recursive tool call handling
- Cancellation signal handling
- Internal method testing
- Different response types (with/without content, tool calls, etc.)