import asyncio
import logging
from datetime import datetime
from pathlib import Path
import signal
from typing import Optional, Any
from types import FrameType

from src.recorder import AudioRecorder, RecordingConfig
from src.config import ConfigManager
from src.cli import parse_args
from src.devices import DeviceManager


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def handle_recording(recorder: AudioRecorder, output_path: Path, 
                          duration: Optional[float]) -> None:
    """Handle the recording process with proper signal handling."""
    
    # Create task for recording
    recording_task = asyncio.create_task(
        recorder.record(output_path, duration)
    )
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig: int, frame: Optional[FrameType]) -> None:
        recorder.stop()
        recording_task.cancel()
        
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await recording_task
    except asyncio.CancelledError:
        logger.info("Recording stopped by user")
        

async def main() -> None:
    # Load config
    config_manager = ConfigManager()
    default_config = config_manager.load()
    
    # Parse command line arguments
    args = parse_args(default_config)
    
    # Handle config management commands
    if args.show_config:
        print("Current configuration:")
        print(f"  Sample rate: {default_config.samplerate} Hz")
        print(f"  Channels: {default_config.channels}")
        print(f"  Output directory: {default_config.output_dir}")
        print(f"  Data type: {default_config.dtype}")
        print(f"  Device: {default_config.device or 'Default'}") 
        print(f"\nConfig file: {config_manager.config_path}")
        return
        
    if args.reset_config:
        config_manager.reset()
        print("Configuration reset to defaults")
        return
    
    # Create recorder with configuration
    config = RecordingConfig(
        samplerate=args.samplerate,
        channels=args.channels,
        dtype=default_config.dtype,
        output_dir=args.output_dir,
        device=args.device
    )
    
    # Save config if requested
    if args.save_config:
        config_manager.save(config)
        print(f"Configuration saved to {config_manager.config_path}")
        return
    
    recorder = AudioRecorder(config)
    
    # Handle device listing
    if args.list_devices:
        devices = await DeviceManager.list_input_devices()
        print("Available input devices:")
        for dev in devices:
            print(f"  {dev.id}: {dev.name} ({dev.channels} ch, {int(dev.samplerate)} Hz)")
        return
    
    # Handle device info request
    if args.info:
        info = await DeviceManager.get_device_info(config.device)
        device_label = f"Device {info.id}" if info.id is not None else "Default Device"
        print(f"{device_label}:")
        print(f"  Name: {info.name}")
        print(f"  Max channels: {info.channels}")
        print(f"  Default sample rate: {info.samplerate} Hz")
        return
    
    # Generate filename if not provided
    filename = args.filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Get device info for filename
        device_info = await DeviceManager.get_device_info(config.device)
        device_id = f"_device{device_info.id}" if device_info.id is not None else ""
        filename = f"recording_{timestamp}{device_id}.wav"
    
    # Ensure .wav extension
    if not filename.endswith('.wav'):
        filename += '.wav'
    
    # Create output path
    output_path = Path(config.output_dir) / filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Start recording
    await handle_recording(recorder, output_path, args.duration)


def run() -> None:
    """Entry point that runs the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    run()