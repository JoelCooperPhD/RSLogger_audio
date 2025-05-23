# RSLogger Audio

A simple command-line audio recording application for macOS, Windows, and Linux.

## Installation

```bash
pip install -e .
```

## Usage

### Basic Recording
```bash
# Record until you press Ctrl+C
python main.py

# Record for 10 seconds
python main.py -d 10

# Record with custom filename
python main.py my_recording.wav
```

### Show Audio Device Info
```bash
python main.py --info
```

### Options
- `-d, --duration`: Recording duration in seconds
- `-r, --samplerate`: Sample rate in Hz (default: 44100)
- `--info`: Display default audio device information

Recordings are saved in the `recordings/` directory by default.
This is an audio module for the RSLogger system
