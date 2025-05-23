import sys
import argparse
from datetime import datetime
from pathlib import Path

from src.recorder import AudioRecorder


def main():
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
    
    recorder = AudioRecorder(samplerate=args.samplerate)
    
    if args.info:
        info = recorder.get_default_device_info()
        print("Default Input Device:")
        print(f"  Name: {info['name']}")
        print(f"  Max channels: {info['channels']}")
        print(f"  Default sample rate: {info['samplerate']} Hz")
        return
    
    # Generate filename if not provided
    if not args.filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.filename = f"recording_{timestamp}.wav"
    
    # Ensure .wav extension
    if not args.filename.endswith('.wav'):
        args.filename += '.wav'
    
    # Create recordings directory if it doesn't exist
    output_path = Path("recordings") / args.filename
    output_path.parent.mkdir(exist_ok=True)
    
    # Record audio
    recorder.record(str(output_path), duration=args.duration)


if __name__ == "__main__":
    main()
