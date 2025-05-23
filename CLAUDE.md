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