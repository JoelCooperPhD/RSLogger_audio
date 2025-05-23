import asyncio
import sounddevice as sd
import soundfile as sf
import numpy as np
import logging
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import json
from datetime import datetime

from .exceptions import RecordingError, DeviceNotFoundError, ConfigurationError
from .enums import AudioFormat, RecordingState
from .devices import DeviceManager, AudioDevice


logger = logging.getLogger(__name__)


@dataclass
class RecordingConfig:
    samplerate: int = 44100
    channels: int = 1
    dtype: str = AudioFormat.FLOAT32.value
    output_dir: str = 'recordings'
    device: Optional[Union[int, str]] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.samplerate <= 0:
            raise ConfigurationError("Sample rate must be positive")
        if self.channels not in (1, 2):
            raise ConfigurationError("Channels must be 1 (mono) or 2 (stereo)")
        if not AudioFormat.is_valid(self.dtype):
            raise ConfigurationError(f"Unsupported dtype: {self.dtype}")
    
    
class AudioRecorder:
    def __init__(self, config: RecordingConfig = RecordingConfig()):
        self.config = config
        self._state = RecordingState.IDLE
        self._recording = False  # Keep for backward compatibility
        self._audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self._device_info: Optional[Dict[str, Any]] = None
        
    def _audio_callback(self, indata: np.ndarray, frames: int, 
                       time_info: Any, status: sd.CallbackFlags) -> None:
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        try:
            self._audio_queue.put_nowait(indata.copy())
        except asyncio.QueueFull:
            logger.warning("Audio queue full, dropping frames")
            
    async def record(self, output_path: Path, duration: Optional[float] = None) -> None:
        logger.info(f"Recording to {output_path}")
        if duration:
            logger.info(f"Recording for {duration} seconds")
        else:
            logger.info("Press Ctrl+C to stop recording")
            
        audio_chunks: list[np.ndarray] = []
        self._state = RecordingState.RECORDING
        self._recording = True  # Keep for backward compatibility
        
        # Get device info before recording
        device_info = await DeviceManager.get_device_info(self.config.device)
        self._device_info = asdict(device_info)
        
        stream = sd.InputStream(
            samplerate=self.config.samplerate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            device=self.config.device,
            callback=self._audio_callback
        )
        
        try:
            with stream:
                start_time = asyncio.get_event_loop().time()
                
                while self._state == RecordingState.RECORDING:
                    if duration and (asyncio.get_event_loop().time() - start_time) >= duration:
                        break
                        
                    try:
                        chunk = await asyncio.wait_for(
                            self._audio_queue.get(), 
                            timeout=0.1
                        )
                        audio_chunks.append(chunk)
                    except asyncio.TimeoutError:
                        continue
                        
        except asyncio.CancelledError:
            logger.info("Recording cancelled")
            raise
        finally:
            self._state = RecordingState.IDLE
            self._recording = False  # Keep for backward compatibility
            await self._save_recording(audio_chunks, output_path)
            
    async def _save_recording(self, audio_chunks: list[np.ndarray], 
                            output_path: Path) -> None:
        if not audio_chunks:
            logger.warning("No audio data recorded")
            return
            
        audio_data = np.concatenate(audio_chunks, axis=0)
        
        # Save audio file asynchronously
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, 
                sf.write, 
                str(output_path), 
                audio_data, 
                self.config.samplerate
            )
        except Exception as e:
            raise RecordingError(f"Failed to save audio file: {e}") from e
        
        duration_seconds = len(audio_data) / self.config.samplerate
        
        # Save metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "device": self._device_info,
            "config": asdict(self.config),
            "audio_file": output_path.name
        }
        
        metadata_path = output_path.with_suffix('.json')
        try:
            await loop.run_in_executor(
                None,
                lambda: metadata_path.write_text(json.dumps(metadata, indent=2))
            )
        except Exception as e:
            # Log error but don't fail the recording
            logger.warning(f"Failed to save metadata: {e}")
        
        logger.info(f"Saved {duration_seconds:.2f} seconds of audio to {output_path}")
        logger.info(f"Metadata saved to {metadata_path}")
        
    def stop(self) -> None:
        """Stop the recording."""
        if self._state == RecordingState.RECORDING:
            self._state = RecordingState.STOPPING
            logger.info("Stopping recording")
        self._recording = False  # Keep for backward compatibility
        
    async def get_device_info(self, device: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """Get device info (for backward compatibility)."""
        device_obj = await DeviceManager.get_device_info(device)
        return asdict(device_obj)
    
    async def list_input_devices(self) -> List[Dict[str, Any]]:
        """List input devices (for backward compatibility)."""
        devices = await DeviceManager.list_input_devices()
        return [asdict(device) for device in devices]