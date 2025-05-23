import asyncio
import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import json
from datetime import datetime


@dataclass
class RecordingConfig:
    samplerate: int = 44100
    channels: int = 1
    dtype: str = 'float32'
    output_dir: str = 'recordings'
    device: Optional[int | str] = None
    
    
class AudioRecorder:
    def __init__(self, config: RecordingConfig = RecordingConfig()):
        self.config = config
        self._recording = False
        self._audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self._device_info: Optional[Dict[str, Any]] = None
        
    def _audio_callback(self, indata: np.ndarray, frames: int, 
                       time_info: Any, status: sd.CallbackFlags) -> None:
        if status:
            print(f"Audio callback status: {status}")
        
        try:
            self._audio_queue.put_nowait(indata.copy())
        except asyncio.QueueFull:
            print("Warning: Audio queue full, dropping frames")
            
    async def record(self, output_path: Path, duration: Optional[float] = None) -> None:
        print(f"Recording to {output_path}...")
        if duration:
            print(f"Recording for {duration} seconds...")
        else:
            print("Press Ctrl+C to stop recording")
            
        audio_chunks: list[np.ndarray] = []
        self._recording = True
        
        # Get device info before recording
        self._device_info = await self.get_device_info(self.config.device)
        
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
                
                while self._recording:
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
            print("\nRecording cancelled")
            raise
        finally:
            self._recording = False
            await self._save_recording(audio_chunks, output_path)
            
    async def _save_recording(self, audio_chunks: list[np.ndarray], 
                            output_path: Path) -> None:
        if not audio_chunks:
            print("No audio data recorded")
            return
            
        audio_data = np.concatenate(audio_chunks, axis=0)
        
        # Save audio file asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            sf.write, 
            str(output_path), 
            audio_data, 
            self.config.samplerate
        )
        
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
        await loop.run_in_executor(
            None,
            lambda: metadata_path.write_text(json.dumps(metadata, indent=2))
        )
        
        print(f"Saved {duration_seconds:.2f} seconds of audio to {output_path}")
        print(f"Metadata saved to {metadata_path}")
        
    def stop(self) -> None:
        self._recording = False
        
    async def get_device_info(self, device: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        device_info = await loop.run_in_executor(
            None,
            sd.query_devices,
            device,
            'input'
        )
        
        # Get device index if device was specified by name
        device_id = device if isinstance(device, int) else None
        if device is None or isinstance(device, str):
            all_devices = await loop.run_in_executor(None, sd.query_devices)
            for idx, dev in enumerate(all_devices):
                if dev['name'] == device_info['name']:
                    device_id = idx
                    break
        
        return {
            'id': device_id,
            'name': device_info['name'],
            'channels': device_info['max_input_channels'],
            'samplerate': device_info['default_samplerate']
        }
    
    async def list_input_devices(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(None, sd.query_devices)
        
        input_devices = []
        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices.append({
                    'id': idx,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'samplerate': device['default_samplerate']
                })
                
        return input_devices