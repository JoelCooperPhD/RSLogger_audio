# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

The planned architecture for this CLI microphone logging application includes:
- Command-line interface for audio recording control
- Audio capture and recording capabilities
- Real-time audio level monitoring in terminal
- File management for recorded audio sessions
- Configuration for audio parameters (sample rate, channels, format)

Currently, only a minimal entry point exists at `main.py`.