#!/usr/bin/env python3
"""
MQTT-controlled audio recorder service for distributed logging systems.

This service connects to an MQTT broker and listens for recording commands
from a master logger. It operates independently and can crash without 
affecting other modules in the system.
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path

from src.mqtt_recorder import MQTTAudioRecorder
from src.config import AudioConfig


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'audio_recorder.log')
        ]
    )


async def main():
    parser = argparse.ArgumentParser(
        description="MQTT-controlled audio recorder module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --id mic1                    # Start with module ID 'mic1'
  %(prog)s --id mic2 --broker 10.0.0.1  # Connect to specific broker
  %(prog)s --id mic3 --port 1884        # Use custom MQTT port
        """
    )
    
    # MQTT configuration
    parser.add_argument("--id", required=True, help="Unique module identifier")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--topic", default="rslogger/audio", help="Base MQTT topic")
    
    # Audio configuration
    parser.add_argument("--samplerate", type=int, help="Override default sample rate")
    parser.add_argument("--channels", type=int, help="Override default channel count")
    parser.add_argument("--device", help="Override default audio device")
    
    # Service configuration
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--config-file", type=Path, help="Load configuration from file")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger("AudioRecorderService")
    
    # Load or create configuration
    if args.config_file and args.config_file.exists():
        config = AudioConfig.load(args.config_file)
        logger.info(f"Loaded configuration from {args.config_file}")
    else:
        config = AudioConfig()
    
    # Override with command line arguments
    if args.samplerate:
        config.samplerate = args.samplerate
    if args.channels:
        config.channels = args.channels
    if args.device:
        config.device = args.device
    
    # Create recorder
    recorder = MQTTAudioRecorder(
        module_id=args.id,
        mqtt_host=args.broker,
        mqtt_port=args.port,
        base_topic=args.topic,
        config=config
    )
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(recorder)))
    
    logger.info(f"Starting MQTT Audio Recorder Service")
    logger.info(f"Module ID: {args.id}")
    logger.info(f"MQTT Broker: {args.broker}:{args.port}")
    logger.info(f"Base Topic: {args.topic}")
    
    try:
        await recorder.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        sys.exit(1)


async def shutdown(recorder: MQTTAudioRecorder):
    """Graceful shutdown handler."""
    logger = logging.getLogger("AudioRecorderService")
    logger.info("Shutting down service...")
    recorder._running = False
    for task in recorder._tasks:
        task.cancel()


if __name__ == "__main__":
    asyncio.run(main())