# MQTT Audio Recorder Module

This module is designed to be part of a distributed logging ecosystem where multiple independent recorder modules can be controlled by a master logger via MQTT.

## Architecture

```
┌─────────────────┐     MQTT Broker      ┌──────────────────┐
│  Master Logger  │◄────────────────────►│ Audio Recorder 1 │
│   Controller    │                       └──────────────────┘
│                 │                       ┌──────────────────┐
│                 │◄────────────────────►│ Audio Recorder 2 │
│                 │                       └──────────────────┘
│                 │                       ┌──────────────────┐
│                 │◄────────────────────►│ Audio Recorder N │
└─────────────────┘                       └──────────────────┘
```

## Key Features

- **Independent Operation**: Each recorder module runs in its own process and can crash without affecting others
- **MQTT Communication**: All control and status messages are exchanged via MQTT
- **Automatic Discovery**: Master controller automatically discovers active recorder modules
- **Heartbeat Monitoring**: Regular heartbeat messages ensure module health
- **Synchronized Recording**: Master can start/stop recording on multiple modules simultaneously

## MQTT Topics

Each audio recorder module uses the following MQTT topics:

- `rslogger/audio/{module_id}/command` - Receives commands from master
- `rslogger/audio/{module_id}/status` - Publishes status updates
- `rslogger/audio/{module_id}/response` - Sends command responses
- `rslogger/audio/{module_id}/data` - Publishes data events (e.g., recording complete)

## Running the System

### 1. Start MQTT Broker

First, you need an MQTT broker running. You can use Mosquitto:

```bash
# Install mosquitto (macOS)
brew install mosquitto

# Start mosquitto
mosquitto -v
```

### 2. Start Audio Recorder Modules

Start one or more audio recorder modules with unique IDs:

```bash
# Terminal 1
python mqtt_recorder_service.py --id mic1

# Terminal 2  
python mqtt_recorder_service.py --id mic2 --device "USB Audio"

# Terminal 3 (with custom settings)
python mqtt_recorder_service.py --id mic3 --samplerate 48000 --channels 2
```

### 3. Start Master Controller

Run the example master controller:

```bash
python master_controller_example.py
```

## Command Protocol

### Start Recording

```json
{
  "command": "start",
  "request_id": "unique-id",
  "duration": 10,  // optional, in seconds
  "recording_id": "session_001",  // optional
  "config": {  // optional config overrides
    "samplerate": 48000,
    "channels": 2
  }
}
```

### Stop Recording

```json
{
  "command": "stop",
  "request_id": "unique-id"
}
```

### Get Status

```json
{
  "command": "status",
  "request_id": "unique-id"
}
```

### Update Configuration

```json
{
  "command": "config",
  "request_id": "unique-id",
  "config": {
    "samplerate": 44100,
    "channels": 1,
    "device": "Built-in Microphone"
  },
  "save": true  // optional, persist config
}
```

### Shutdown Module

```json
{
  "command": "shutdown",
  "request_id": "unique-id"
}
```

## Status Messages

Modules publish status updates regularly:

```json
{
  "module_id": "mic1",
  "state": "recording",  // idle, recording, error, disconnected
  "timestamp": "2025-01-23T12:00:00.000Z",
  "recording_id": "session_001",  // when recording
  "config": {
    "samplerate": 44100,
    "channels": 1,
    "device": "Built-in Microphone"
  }
}
```

## Configuration File

You can create a configuration file for persistent settings:

```json
{
  "module_id": "mic1",
  "mqtt": {
    "host": "localhost",
    "port": 1883,
    "base_topic": "rslogger/audio"
  },
  "audio": {
    "samplerate": 44100,
    "channels": 1,
    "device": null,
    "recording_dir": "./recordings"
  },
  "log_level": "INFO",
  "enable_heartbeat": true,
  "heartbeat_interval": 30
}
```

Load with: `python mqtt_recorder_service.py --id mic1 --config-file config.json`

## Integration Example

```python
# In your master logger
import asyncio
from master_controller_example import MasterController

async def main():
    controller = MasterController()
    
    # Start controller
    asyncio.create_task(controller.start())
    
    # Wait for modules to connect
    await asyncio.sleep(2)
    
    # Start synchronized recording on all modules
    results = await controller.start_all_recordings(duration=60)
    
    # Check status
    status = controller.get_module_status()
    for module_id, info in status.items():
        print(f"{module_id}: {info['state']}")
    
    # Stop all recordings
    await controller.stop_all_recordings()

asyncio.run(main())
```

## Fault Tolerance

- Each module runs independently - if one crashes, others continue
- Master controller tracks module health via heartbeats
- Automatic reconnection on MQTT connection loss
- Graceful shutdown on SIGTERM/SIGINT signals
- Recording files are saved even if module crashes mid-recording

## Deployment

For production deployment:

1. Use systemd service files for each recorder module
2. Configure MQTT broker with authentication and TLS
3. Set up log rotation for module logs
4. Monitor module health with the master controller
5. Use persistent MQTT sessions for reliability