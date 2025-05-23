import asyncio
import argparse
from datetime import datetime
from pathlib import Path
import signal
from typing import Optional

from src.recorder import AudioRecorder, RecordingConfig


async def handle_recording(recorder: AudioRecorder, output_path: Path, 
                          duration: Optional[float]) -> None:
    """Handle the recording process with proper signal handling."""
    
    # Create task for recording
    recording_task = asyncio.create_task(
        recorder.record(output_path, duration)
    )
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        recorder.stop()
        recording_task.cancel()
        
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await recording_task
    except asyncio.CancelledError:
        print("\nRecording stopped by user")
        

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="RSLogger Audio - Simple audio recording CLI"
    )
    
    parser.add_argument(
        "filename",
        nargs="?",
        help="Output filename (default: timestamp-based name)"
    )
    
    parser.add_argument(
        "-d", "--duration",
        type=float,
        help="Recording duration in seconds (default: record until Ctrl+C)"
    )
    
    parser.add_argument(
        "-r", "--samplerate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)"
    )
    
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show default audio device information"
    )
    
    args = parser.parse_args()
    
    # Create recorder with configuration
    config = RecordingConfig(samplerate=args.samplerate)
    recorder = AudioRecorder(config)
    
    # Handle device info request
    if args.info:
        info = await recorder.get_device_info()
        print("Default Input Device:")
        print(f"  Name: {info['name']}")
        print(f"  Max channels: {info['channels']}")
        print(f"  Default sample rate: {info['samplerate']} Hz")
        return
    
    # Generate filename if not provided
    filename = args.filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
    
    # Ensure .wav extension
    if not filename.endswith('.wav'):
        filename += '.wav'
    
    # Create output path
    output_path = Path("recordings") / filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Start recording
    await handle_recording(recorder, output_path, args.duration)


def run() -> None:
    """Entry point that runs the async main function."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    run()