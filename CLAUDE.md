# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Guidelines

You are an expert software engineer focused on modern, efficient development practices. Follow these core principles:

**Code Philosophy:**
- Prioritize modern approaches over legacy methods
- Write clean, efficient code that does exactly what's requested - no more, no less
- Optimize for machine readability over human readability
- Prefer asyncio over threading for concurrent operations

**Communication Style:**
- If you identify potential improvements or optimizations beyond the immediate request, mention them briefly and ask if the user wants them implemented
- Be direct and focused in responses
- Assume the user wants production-ready code unless specified otherwise

**Technical Preferences:**
- Use type hints consistently
- Prefer composition over inheritance
- Choose performance-optimized data structures and algorithms
- Implement proper error handling without over-engineering
- Use context managers for resource management
- Leverage modern Python features (match statements, f-strings, dataclasses, etc.)

**Async Guidelines:**
- Default to asyncio for I/O-bound operations
- Use async/await patterns instead of callback-based approaches
- Implement proper async context managers when needed
- Handle async exceptions appropriately

Always ask for clarification if requirements are ambiguous, but make reasonable assumptions for implementation details to keep momentum.

## Project Overview

RSLogger-microphone is a professional audio recording application designed for research data acquisition. It provides both standalone operation and distributed MQTT-based control for integration into larger logging ecosystems.

**Current Status**: Fully functional with comprehensive test coverage (85%). The module can operate independently or as part of a distributed system controlled via MQTT.

## Development Commands

```bash
# Install dependencies
pip install -e .

# Run the application
python main.py [options]

# Basic recording (saves to recordings/ directory)
python main.py

# Record with custom settings
python main.py --duration 10 --samplerate 48000 --channels 2

# Device management
python main.py --list-devices  # List all available audio devices
python main.py --info          # Show detailed system audio info
python main.py --device "USB Audio"  # Use specific device by name

# Configuration management
python main.py --save-config   # Save current settings as defaults
python main.py --show-config   # Display current configuration
python main.py --reset-config  # Reset to factory defaults

# Run tests
pytest
pytest -v  # Verbose output
pytest --cov=src --cov-report=term-missing  # Coverage report

# MQTT Module Operation
python mqtt_recorder_service.py --id mic1  # Start MQTT-controlled recorder
python mqtt_recorder_service.py --id mic1 --broker mqtt.example.com  # Custom broker
python master_controller_example.py  # Run example master controller
```

## Architecture Notes

### Standalone Operation

**Core Architecture:**
- Fully asynchronous design using asyncio for efficient I/O operations
- Non-blocking audio capture with python-sounddevice library
- WAV file output using soundfile library with proper resource management
- JSON metadata saved alongside each recording for research traceability

**Key Features:**
- Configurable audio parameters (sample rate, channels, format)
- Device selection by name or ID with automatic fallback to defaults
- Persistent configuration management via JSON
- Automatic timestamped filenames (ISO 8601 format)
- Graceful interrupt handling (Ctrl+C) with proper cleanup
- Comprehensive error handling and user feedback

### MQTT Distributed Operation

**Architecture:**
- Independent process operation - module crashes don't affect other components
- MQTT pub/sub communication for loose coupling
- Master-slave control pattern with multiple recorder modules
- Automatic module discovery and health monitoring
- Synchronized recording across multiple devices

**MQTT Components:**
- `src/mqtt_recorder.py`: MQTT-enabled audio recorder with command handling
- `src/mqtt_config.py`: Extended configuration for MQTT settings
- `mqtt_recorder_service.py`: Service entry point for MQTT modules
- `master_controller_example.py`: Example master controller implementation

**MQTT Topics:**
- `rslogger/audio/{module_id}/command`: Receives control commands
- `rslogger/audio/{module_id}/status`: Publishes module status
- `rslogger/audio/{module_id}/response`: Command acknowledgments
- `rslogger/audio/{module_id}/data`: Data events (recording complete, etc.)

**Key Components:**
- `main.py`: Standalone CLI entry point
- `src/recorder.py`: Core async AudioRecorder class
- `src/config.py`: Basic configuration management
- `src/mqtt_recorder.py`: MQTT wrapper for distributed operation

**Data Flow:**
1. Audio callback fills asyncio.Queue with numpy arrays
2. Async coroutine consumes queue and writes to disk
3. Metadata JSON created with recording parameters
4. MQTT events published for master controller tracking
5. All operations handled asynchronously for optimal performance

## Dependencies

Core dependencies as defined in `pyproject.toml`:
- Python 3.11+
- sounddevice: Cross-platform audio I/O
- soundfile: Reading and writing audio files
- numpy: Efficient array operations for audio data
- asyncio-mqtt: MQTT client for distributed operation

Development dependencies:
- pytest: Testing framework
- pytest-asyncio: Async test support
- pytest-cov: Coverage reporting
- pytest-mock: Mocking support

## Testing

The project includes a comprehensive test suite with 85% code coverage:
- `tests/test_recorder.py`: Tests for audio recording functionality
- `tests/test_config.py`: Tests for configuration management
- `tests/test_cli.py`: Tests for CLI argument parsing
- `tests/test_mqtt_recorder.py`: Tests for MQTT recorder functionality
- `tests/test_mqtt_config.py`: Tests for MQTT configuration
- `tests/conftest.py`: Shared pytest fixtures

Run tests with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Usage Examples

### Standalone Recording
```bash
# Basic recording
python main.py

# Record for 30 seconds with custom settings
python main.py --duration 30 --samplerate 48000 --channels 2

# Use specific device
python main.py --device "USB Microphone" --duration 60
```

### Distributed MQTT Recording
```bash
# Terminal 1 - Start MQTT broker
mosquitto -v

# Terminal 2 - Start first recorder module
python mqtt_recorder_service.py --id mic1

# Terminal 3 - Start second recorder module  
python mqtt_recorder_service.py --id mic2 --device "USB Audio"

# Terminal 4 - Control from master
python master_controller_example.py
# Then use menu to start/stop recordings on all modules
```