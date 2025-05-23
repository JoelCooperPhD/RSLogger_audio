import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from enum import Enum

import asyncio_mqtt as aiomqtt
import sounddevice as sd
import numpy as np

from .recorder import AudioRecorder, RecordingConfig
from .mqtt_config import AudioConfig


class RecorderState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class RecorderCommand(str, Enum):
    START = "start"
    STOP = "stop"
    STATUS = "status"
    CONFIG = "config"
    SHUTDOWN = "shutdown"


class MQTTAudioRecorder:
    """MQTT-controlled audio recorder module for distributed logging systems."""
    
    def __init__(
        self,
        module_id: str,
        mqtt_host: str = "localhost",
        mqtt_port: int = 1883,
        base_topic: str = "rslogger/audio",
        config: Optional[AudioConfig] = None
    ):
        self.module_id = module_id
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.base_topic = base_topic
        
        # MQTT topics
        self.command_topic = f"{base_topic}/{module_id}/command"
        self.status_topic = f"{base_topic}/{module_id}/status"
        self.data_topic = f"{base_topic}/{module_id}/data"
        
        # State
        self.state = RecorderState.DISCONNECTED
        self.audio_config = config or AudioConfig()
        self.recorder: Optional[AudioRecorder] = None
        self.recording_config: Optional[RecordingConfig] = None
        self.current_recording_id: Optional[str] = None
        
        # Logging
        self.logger = logging.getLogger(f"MQTTRecorder-{module_id}")
        
        # Control
        self._running = False
        self._tasks: list[asyncio.Task] = []
        
    async def start(self) -> None:
        """Start the MQTT recorder module."""
        self._running = True
        self.logger.info(f"Starting MQTT Audio Recorder: {self.module_id}")
        
        async with aiomqtt.Client(self.mqtt_host, self.mqtt_port) as client:
            self.mqtt_client = client
            
            # Subscribe to command topic
            await client.subscribe(self.command_topic)
            
            # Announce presence
            await self._update_status("connected")
            
            # Start background tasks
            self._tasks = [
                asyncio.create_task(self._handle_messages()),
                asyncio.create_task(self._heartbeat_loop()),
            ]
            
            try:
                await asyncio.gather(*self._tasks)
            except asyncio.CancelledError:
                self.logger.info("Shutting down...")
            finally:
                await self._cleanup()
    
    async def _handle_messages(self) -> None:
        """Handle incoming MQTT messages."""
        async for message in self.mqtt_client.messages:
            try:
                payload = json.loads(message.payload.decode())
                command = payload.get("command")
                
                self.logger.debug(f"Received command: {command}")
                
                if command == RecorderCommand.START:
                    await self._handle_start(payload)
                elif command == RecorderCommand.STOP:
                    await self._handle_stop(payload)
                elif command == RecorderCommand.STATUS:
                    await self._send_status()
                elif command == RecorderCommand.CONFIG:
                    await self._handle_config(payload)
                elif command == RecorderCommand.SHUTDOWN:
                    await self._handle_shutdown()
                else:
                    self.logger.warning(f"Unknown command: {command}")
                    
            except json.JSONDecodeError:
                self.logger.error(f"Invalid JSON in message: {message.payload}")
            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
                await self._update_status("error", {"error": str(e)})
    
    async def _handle_start(self, payload: Dict[str, Any]) -> None:
        """Handle start recording command."""
        if self.state == RecorderState.RECORDING:
            await self._send_response(payload.get("request_id"), False, "Already recording")
            return
        
        try:
            # Update config if provided
            if "config" in payload:
                self._update_config(payload["config"])
            
            # Generate recording ID
            self.current_recording_id = payload.get("recording_id", 
                                                   datetime.now().strftime("%Y%m%d_%H%M%S"))
            
            # Create recording config from audio config
            self.recording_config = RecordingConfig(
                samplerate=self.audio_config.samplerate,
                channels=self.audio_config.channels,
                device=self.audio_config.device,
                dtype=self.audio_config.dtype,
                output_dir=str(self.audio_config.recording_dir)
            )
            
            # Create recorder
            self.recorder = AudioRecorder(self.recording_config)
            
            # Start recording
            duration = payload.get("duration")
            filename = f"recording_{self.current_recording_id}_{self.module_id}.wav"
            
            # Start recording in background
            asyncio.create_task(self._recording_task(filename, duration))
            
            self.state = RecorderState.RECORDING
            await self._update_status("recording", {
                "recording_id": self.current_recording_id,
                "filename": filename,
                "config": self.audio_config.to_dict()
            })
            
            await self._send_response(payload.get("request_id"), True, "Recording started")
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            await self._send_response(payload.get("request_id"), False, str(e))
            await self._update_status("error", {"error": str(e)})
    
    async def _recording_task(self, filename: str, duration: Optional[float]) -> None:
        """Background task for recording."""
        try:
            await self.recorder.record(filename, duration)
            
            # Send completion notification
            await self._publish_data({
                "event": "recording_complete",
                "recording_id": self.current_recording_id,
                "filename": filename,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Recording error: {e}")
            await self._update_status("error", {"error": str(e)})
        finally:
            self.state = RecorderState.IDLE
            self.recorder = None
            self.current_recording_id = None
            await self._update_status("idle")
    
    async def _handle_stop(self, payload: Dict[str, Any]) -> None:
        """Handle stop recording command."""
        if self.state != RecorderState.RECORDING:
            await self._send_response(payload.get("request_id"), False, "Not recording")
            return
        
        try:
            if self.recorder:
                await self.recorder.stop()
            
            await self._send_response(payload.get("request_id"), True, "Recording stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            await self._send_response(payload.get("request_id"), False, str(e))
    
    async def _handle_config(self, payload: Dict[str, Any]) -> None:
        """Handle configuration update."""
        try:
            if "config" in payload:
                self._update_config(payload["config"])
                if payload.get("save", False):
                    self.audio_config.save()
            
            await self._send_response(payload.get("request_id"), True, 
                                    data={"config": self.audio_config.to_dict()})
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            await self._send_response(payload.get("request_id"), False, str(e))
    
    async def _handle_shutdown(self) -> None:
        """Handle shutdown command."""
        self.logger.info("Received shutdown command")
        self._running = False
        
        # Stop any ongoing recording
        if self.recorder:
            await self.recorder.stop()
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages."""
        while self._running:
            await self._send_status()
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    async def _update_status(self, state: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Update and publish module status."""
        self.state = RecorderState(state)
        await self._send_status(data)
    
    async def _send_status(self, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """Send current status."""
        status = {
            "module_id": self.module_id,
            "state": self.state.value,
            "timestamp": datetime.now().isoformat(),
            "config": self.audio_config.to_dict(),
        }
        
        if additional_data:
            status.update(additional_data)
        
        if self.state == RecorderState.RECORDING and self.current_recording_id:
            status["recording_id"] = self.current_recording_id
        
        await self.mqtt_client.publish(self.status_topic, json.dumps(status))
    
    async def _send_response(self, request_id: Optional[str], success: bool, 
                           message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        """Send command response."""
        response = {
            "request_id": request_id,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            response["data"] = data
        
        response_topic = f"{self.base_topic}/{self.module_id}/response"
        await self.mqtt_client.publish(response_topic, json.dumps(response))
    
    async def _publish_data(self, data: Dict[str, Any]) -> None:
        """Publish data events."""
        await self.mqtt_client.publish(self.data_topic, json.dumps(data))
    
    def _update_config(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        if "samplerate" in config_dict:
            self.audio_config.samplerate = config_dict["samplerate"]
        if "channels" in config_dict:
            self.audio_config.channels = config_dict["channels"]
        if "device" in config_dict:
            self.audio_config.device = config_dict["device"]
        if "recording_dir" in config_dict:
            self.audio_config.recording_dir = Path(config_dict["recording_dir"])
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self.recorder:
            await self.recorder.stop()
        
        await self._update_status("disconnected")