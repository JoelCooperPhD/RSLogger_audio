"""Tests for MQTT audio recorder functionality."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from pathlib import Path

import asyncio_mqtt as aiomqtt

from src.mqtt_recorder import (
    MQTTAudioRecorder, RecorderState, RecorderCommand
)
from src.mqtt_config import AudioConfig
from src.recorder import RecordingConfig


class TestMQTTAudioRecorder:
    """Test MQTT audio recorder functionality."""
    
    @pytest.fixture
    def audio_config(self):
        """Create test audio configuration."""
        return AudioConfig(
            samplerate=44100,
            channels=1,
            device=None,
            recording_dir=Path("test_recordings")
        )
    
    @pytest.fixture
    def mqtt_recorder(self, audio_config):
        """Create MQTT audio recorder instance."""
        return MQTTAudioRecorder(
            module_id="test_module",
            mqtt_host="localhost",
            mqtt_port=1883,
            base_topic="test/audio",
            config=audio_config
        )
    
    def test_initialization(self, mqtt_recorder):
        """Test recorder initialization."""
        assert mqtt_recorder.module_id == "test_module"
        assert mqtt_recorder.mqtt_host == "localhost"
        assert mqtt_recorder.mqtt_port == 1883
        assert mqtt_recorder.base_topic == "test/audio"
        assert mqtt_recorder.command_topic == "test/audio/test_module/command"
        assert mqtt_recorder.status_topic == "test/audio/test_module/status"
        assert mqtt_recorder.data_topic == "test/audio/test_module/data"
        assert mqtt_recorder.state == RecorderState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_start_recording_command(self, mqtt_recorder):
        """Test handling start recording command."""
        # Mock the recorder
        with patch('src.mqtt_recorder.AudioRecorder') as mock_recorder_class:
            mock_recorder = AsyncMock()
            mock_recorder_class.return_value = mock_recorder
            
            # Mock MQTT client
            mqtt_recorder.mqtt_client = AsyncMock()
            
            # Create start command
            payload = {
                "command": "start",
                "request_id": "test_123",
                "duration": 10,
                "recording_id": "test_recording"
            }
            
            # Handle start command
            await mqtt_recorder._handle_start(payload)
            
            # Verify state changed
            assert mqtt_recorder.state == RecorderState.RECORDING
            assert mqtt_recorder.current_recording_id == "test_recording"
            
            # Verify recorder was created with correct config
            mock_recorder_class.assert_called_once()
            config = mock_recorder_class.call_args[0][0]
            assert isinstance(config, RecordingConfig)
            assert config.samplerate == 44100
            assert config.channels == 1
    
    @pytest.mark.asyncio
    async def test_stop_recording_command(self, mqtt_recorder):
        """Test handling stop recording command."""
        # Setup recorder in recording state
        mqtt_recorder.state = RecorderState.RECORDING
        mqtt_recorder.recorder = AsyncMock()
        mqtt_recorder.mqtt_client = AsyncMock()
        
        # Create stop command
        payload = {
            "command": "stop",
            "request_id": "test_456"
        }
        
        # Handle stop command
        await mqtt_recorder._handle_stop(payload)
        
        # Verify recorder was stopped
        mqtt_recorder.recorder.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_config_update_command(self, mqtt_recorder):
        """Test handling configuration update."""
        mqtt_recorder.mqtt_client = AsyncMock()
        
        # Create config command
        payload = {
            "command": "config",
            "request_id": "test_789",
            "config": {
                "samplerate": 48000,
                "channels": 2
            },
            "save": False
        }
        
        # Handle config command
        await mqtt_recorder._handle_config(payload)
        
        # Verify config was updated
        assert mqtt_recorder.audio_config.samplerate == 48000
        assert mqtt_recorder.audio_config.channels == 2
    
    @pytest.mark.asyncio
    async def test_status_publishing(self, mqtt_recorder):
        """Test status message publishing."""
        mqtt_recorder.mqtt_client = AsyncMock()
        mqtt_recorder.state = RecorderState.IDLE
        
        # Send status
        await mqtt_recorder._send_status()
        
        # Verify status was published
        mqtt_recorder.mqtt_client.publish.assert_called_once()
        call_args = mqtt_recorder.mqtt_client.publish.call_args
        
        assert call_args[0][0] == "test/audio/test_module/status"
        
        status_data = json.loads(call_args[0][1])
        assert status_data["module_id"] == "test_module"
        assert status_data["state"] == "idle"
        assert "timestamp" in status_data
        assert "config" in status_data
    
    @pytest.mark.asyncio
    async def test_heartbeat_loop(self, mqtt_recorder):
        """Test heartbeat functionality."""
        mqtt_recorder.mqtt_client = AsyncMock()
        mqtt_recorder._running = True
        
        # Run heartbeat for a short time
        heartbeat_task = asyncio.create_task(mqtt_recorder._heartbeat_loop())
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Stop the loop
        mqtt_recorder._running = False
        heartbeat_task.cancel()
        
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        
        # Verify at least one status was sent
        mqtt_recorder.mqtt_client.publish.assert_called()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mqtt_recorder):
        """Test error handling in recording."""
        with patch('src.mqtt_recorder.AudioRecorder') as mock_recorder_class:
            # Make recorder creation fail
            mock_recorder_class.side_effect = Exception("Test error")
            
            mqtt_recorder.mqtt_client = AsyncMock()
            
            # Try to start recording
            payload = {
                "command": "start",
                "request_id": "test_error"
            }
            
            await mqtt_recorder._handle_start(payload)
            
            # Verify error response was sent
            response_calls = [
                call for call in mqtt_recorder.mqtt_client.publish.call_args_list
                if "response" in call[0][0]
            ]
            
            assert len(response_calls) > 0
            response_data = json.loads(response_calls[0][0][1])
            assert response_data["success"] is False
            assert "Test error" in response_data["message"]
    
    @pytest.mark.asyncio
    async def test_shutdown_command(self, mqtt_recorder):
        """Test shutdown functionality."""
        mqtt_recorder._running = True
        mqtt_recorder.recorder = AsyncMock()
        
        # Create a proper mock task
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        mqtt_recorder._tasks = [mock_task]
        
        # Handle shutdown
        await mqtt_recorder._handle_shutdown()
        
        # Verify shutdown actions
        assert mqtt_recorder._running is False
        mqtt_recorder.recorder.stop.assert_called_once()
        mock_task.cancel.assert_called_once()
    
    def test_config_update_partial(self, mqtt_recorder):
        """Test partial configuration updates."""
        original_samplerate = mqtt_recorder.audio_config.samplerate
        
        # Update only device
        mqtt_recorder._update_config({"device": "USB Microphone"})
        
        # Verify only device changed
        assert mqtt_recorder.audio_config.device == "USB Microphone"
        assert mqtt_recorder.audio_config.samplerate == original_samplerate
    
    @pytest.mark.asyncio
    async def test_recording_completion_event(self, mqtt_recorder):
        """Test recording completion event publishing."""
        mqtt_recorder.mqtt_client = AsyncMock()
        
        # Simulate recording completion
        await mqtt_recorder._publish_data({
            "event": "recording_complete",
            "recording_id": "test_123",
            "filename": "test.wav",
            "timestamp": datetime.now().isoformat()
        })
        
        # Verify data was published
        mqtt_recorder.mqtt_client.publish.assert_called_once()
        call_args = mqtt_recorder.mqtt_client.publish.call_args
        
        assert call_args[0][0] == "test/audio/test_module/data"
        data = json.loads(call_args[0][1])
        assert data["event"] == "recording_complete"