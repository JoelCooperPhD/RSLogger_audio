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

RSLogger_microphone is a microphone logging application designed for audio data acquisition and recording for research purposes.

**Current Status**: Initial skeleton - core functionality not yet implemented.

## Development Commands

```bash
# Run the application
python3 main.py

# Install dependencies (when added)
pip install -e .
```

## Architecture Notes

Current implementation:
- Simple CLI using argparse for audio recording control
- Audio capture using python-sounddevice library
- WAV file output using soundfile library
- Default microphone recording with configurable sample rate
- Automatic timestamped filenames
- Recordings saved to `recordings/` directory

Key components:
- `main.py`: CLI entry point with argument parsing
- `src/recorder.py`: Core AudioRecorder class using sounddevice callbacks
- Queue-based audio data collection for smooth recording