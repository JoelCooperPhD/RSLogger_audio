import sounddevice as sd
import soundfile as sf
import numpy as np
from typing import Optional
import time
import threading
import queue


class AudioRecorder:
    def __init__(self, samplerate: int = 44100, channels: int = 1):
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.audio_queue = queue.Queue()
        
    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_queue.put(indata.copy())
        
    def record(self, filename: str, duration: Optional[float] = None):
        print(f"Recording to {filename}...")
        print("Press Ctrl+C to stop recording" if not duration else f"Recording for {duration} seconds...")
        
        audio_data = []
        
        with sd.InputStream(samplerate=self.samplerate,
                          channels=self.channels,
                          callback=self.callback):
            
            start_time = time.time()
            self.recording = True
            
            try:
                while self.recording:
                    if duration and (time.time() - start_time) >= duration:
                        break
                    
                    try:
                        data = self.audio_queue.get(timeout=0.1)
                        audio_data.append(data)
                    except queue.Empty:
                        continue
                        
            except KeyboardInterrupt:
                print("\nRecording stopped by user")
            
            self.recording = False
        
        if audio_data:
            audio_array = np.concatenate(audio_data, axis=0)
            sf.write(filename, audio_array, self.samplerate)
            duration_recorded = len(audio_array) / self.samplerate
            print(f"Saved {duration_recorded:.2f} seconds of audio to {filename}")
        else:
            print("No audio data recorded")
    
    def get_default_device_info(self):
        device_info = sd.query_devices(kind='input')
        return {
            'name': device_info['name'],
            'channels': device_info['max_input_channels'],
            'samplerate': device_info['default_samplerate']
        }