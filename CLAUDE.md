# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LangGraph is a low-level orchestration framework for building stateful, long-running agents and workflows. It follows a Pregel-inspired architecture pattern with state graphs, channels, and checkpointers for durable execution.

## Essential Development Commands

### Monorepo-level Commands
```bash
make all           # Run lint, format, lock, test across all libraries
make install       # Install dependencies for all projects
make test          # Test all projects
make lint          # Lint all projects
make format        # Format all projects
```

### Library-specific Commands (from libs/[library]/)
```bash
make format        # Format code with ruff
make lint          # Run ruff + mypy type checking
make test          # Run pytest test suite
make coverage      # Generate test coverage report
make test_watch    # Run tests in watch mode
TEST=path/to/test.py make test  # Run specific test file
```

### Database Testing (for checkpoint libraries)
```bash
make start-postgres  # Start PostgreSQL container for tests
make stop-postgres   # Stop PostgreSQL container
```

## High-Level Architecture

### Core Execution Model
LangGraph implements a **Pregel-inspired state graph** architecture:
- **StateGraph**: Central abstraction for building workflows with typed state
- **Nodes**: Functions that process and update state
- **Edges**: Define control flow between nodes (normal, conditional, entry points)
- **Channels**: Communication primitives (last_value, any_value, topic, etc.)
- **Checkpointers**: Persistence layer for state durability and time-travel

### Key Architectural Components

1. **Execution Engine** (`libs/langgraph/langgraph/pregel/`):
   - `Pregel` class orchestrates graph execution
   - Handles concurrent node execution, retry logic, and state management
   - Implements streaming, async support, and subgraph execution

2. **State Management** (`libs/langgraph/langgraph/graph/state.py`):
   - `StateGraph` provides typed state handling
   - Automatic state merging via reducers
   - Support for annotations and state schemas

3. **Channel System** (`libs/langgraph/langgraph/channels/`):
   - Different channel types for various communication patterns
   - `LastValue`: Overwrites with latest value
   - `AnyValue`: Accepts any value updates
   - `Topic`: Pub/sub pattern for multiple consumers

4. **Checkpoint System** (separate libraries):
   - Base interfaces in `libs/checkpoint/`
   - SQLite implementation in `libs/checkpoint-sqlite/`
   - PostgreSQL implementation in `libs/checkpoint-postgres/`
   - Enables state persistence, time-travel, and fault tolerance

5. **Prebuilt Components** (`libs/prebuilt/`):
   - Higher-level abstractions for common patterns
   - React agents, tool nodes, and function calling
   - Built on top of core LangGraph primitives

### Monorepo Structure
```
libs/
├── langgraph/         # Core framework
├── prebuilt/          # High-level agent APIs
├── checkpoint/        # Base checkpoint interfaces
├── checkpoint-sqlite/ # SQLite persistence
├── checkpoint-postgres/ # PostgreSQL persistence
├── cli/              # LangGraph CLI tool
├── sdk-py/           # Python SDK for platform
└── sdk-js/           # JavaScript/TypeScript SDK
```

## Testing Strategy

- **Framework**: pytest with parallel execution support
- **Test Organization**: Tests mirror source structure in `tests/` directories
- **Database Tests**: Use Docker Compose for PostgreSQL integration tests
- **Coverage**: Aim for high coverage, use `make coverage` to check
- **Mocking**: Custom fake implementations for external dependencies (see `tests/fake_*.py`)

## Development Guidelines

1. **Backwards Compatibility**: Never break existing public APIs
2. **Type Safety**: All code must pass mypy strict type checking
3. **Testing**: Bug fixes require failing tests that demonstrate the issue
4. **Formatting**: Use `make format` before committing (ruff formatter)
5. **Dependencies**: Changes to core libraries may impact dependent libraries - test accordingly
6. **State Updates**: When modifying state handling, ensure compatibility with all channel types
7. **Async Support**: Maintain both sync and async implementations where applicable

## Common Development Tasks

### Adding a New Node Type
1. Define the node function with proper type hints
2. Ensure it accepts state and returns state updates
3. Add comprehensive tests including edge cases
4. Update relevant examples if the pattern is reusable

### Modifying State Channels
1. Changes to channels affect state propagation across the entire graph
2. Test with different checkpoint implementations
3. Verify concurrent execution behavior
4. Check compatibility with existing channel types

### Working with Checkpointers
1. Follow the base checkpoint interface in `libs/checkpoint/`
2. Implement both sync and async versions
3. Test state persistence, retrieval, and listing operations
4. Ensure proper serialization of complex state types

### Debugging Graph Execution
1. Use `stream_mode="debug"` for detailed execution traces
2. Check `libs/langgraph/langgraph/pregel/debug.py` for debug utilities
3. Leverage checkpoint history for state inspection
4. Use LangSmith integration for production debugging