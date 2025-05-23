"""Tests for MQTT configuration functionality."""

import json
import pytest
from pathlib import Path
import tempfile

from src.mqtt_config import MQTTConfig, AudioConfig, ModuleConfig


class TestMQTTConfig:
    """Test MQTT configuration."""
    
    def test_mqtt_config_defaults(self):
        """Test MQTT config default values."""
        config = MQTTConfig()
        assert config.host == "localhost"
        assert config.port == 1883
        assert config.base_topic == "rslogger/audio"
        assert config.username is None
        assert config.password is None
        assert config.tls_enabled is False
        assert config.keepalive == 60
        assert config.reconnect_interval == 5
    
    def test_mqtt_config_custom(self):
        """Test MQTT config with custom values."""
        config = MQTTConfig(
            host="broker.example.com",
            port=8883,
            username="user",
            password="pass",
            tls_enabled=True
        )
        assert config.host == "broker.example.com"
        assert config.port == 8883
        assert config.username == "user"
        assert config.password == "pass"
        assert config.tls_enabled is True


class TestAudioConfig:
    """Test audio configuration."""
    
    def test_audio_config_defaults(self):
        """Test audio config default values."""
        config = AudioConfig()
        assert config.samplerate == 44100
        assert config.channels == 1
        assert config.device is None
        assert config.dtype == "float32"
        assert isinstance(config.recording_dir, Path)
        assert config.recording_dir == Path("recordings")
    
    def test_audio_config_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = AudioConfig(recording_dir="test/path")
        assert isinstance(config.recording_dir, Path)
        assert config.recording_dir == Path("test/path")
    
    def test_audio_config_to_dict(self):
        """Test conversion to dictionary."""
        config = AudioConfig(
            samplerate=48000,
            channels=2,
            device="USB Mic",
            recording_dir=Path("my/recordings")
        )
        
        data = config.to_dict()
        assert data["samplerate"] == 48000
        assert data["channels"] == 2
        assert data["device"] == "USB Mic"
        assert data["recording_dir"] == "my/recordings"
        assert isinstance(data["recording_dir"], str)
    
    def test_audio_config_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "samplerate": 48000,
            "channels": 2,
            "device": "USB Mic",
            "recording_dir": "my/recordings"
        }
        
        config = AudioConfig.from_dict(data)
        assert config.samplerate == 48000
        assert config.channels == 2
        assert config.device == "USB Mic"
        assert config.recording_dir == Path("my/recordings")
    
    def test_audio_config_save_load(self):
        """Test saving and loading audio config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Create and save config
            config = AudioConfig(samplerate=48000, channels=2)
            config.save(temp_path)
            
            # Load config
            loaded = AudioConfig.load(temp_path)
            assert loaded.samplerate == 48000
            assert loaded.channels == 2
            
        finally:
            temp_path.unlink()
    
    def test_audio_config_load_nonexistent(self):
        """Test loading from non-existent file returns defaults."""
        config = AudioConfig.load(Path("nonexistent.json"))
        assert config.samplerate == 44100  # Default value


class TestModuleConfig:
    """Test complete module configuration."""
    
    def test_module_config_initialization(self):
        """Test module config initialization."""
        config = ModuleConfig(module_id="test_module")
        assert config.module_id == "test_module"
        assert isinstance(config.mqtt, MQTTConfig)
        assert isinstance(config.audio, AudioConfig)
        assert config.log_level == "INFO"
        assert config.enable_heartbeat is True
        assert config.heartbeat_interval == 30
    
    def test_module_config_to_dict(self):
        """Test conversion to dictionary."""
        config = ModuleConfig(
            module_id="test_module",
            log_level="DEBUG"
        )
        
        data = config.to_dict()
        assert data["module_id"] == "test_module"
        assert data["log_level"] == "DEBUG"
        assert "mqtt" in data
        assert "audio" in data
        assert isinstance(data["mqtt"], dict)
        assert isinstance(data["audio"], dict)
    
    def test_module_config_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "module_id": "test_module",
            "mqtt": {
                "host": "broker.test",
                "port": 1884
            },
            "audio": {
                "samplerate": 48000,
                "channels": 2
            },
            "log_level": "DEBUG",
            "enable_heartbeat": False
        }
        
        config = ModuleConfig.from_dict(data)
        assert config.module_id == "test_module"
        assert config.mqtt.host == "broker.test"
        assert config.mqtt.port == 1884
        assert config.audio.samplerate == 48000
        assert config.audio.channels == 2
        assert config.log_level == "DEBUG"
        assert config.enable_heartbeat is False
    
    def test_module_config_save_load(self):
        """Test saving and loading complete module config."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            # Create and save config
            config = ModuleConfig(
                module_id="test_module",
                log_level="DEBUG"
            )
            config.mqtt.host = "test.broker"
            config.audio.samplerate = 48000
            
            config.save(temp_path)
            
            # Load config
            loaded = ModuleConfig.load(temp_path)
            assert loaded.module_id == "test_module"
            assert loaded.log_level == "DEBUG"
            assert loaded.mqtt.host == "test.broker"
            assert loaded.audio.samplerate == 48000
            
        finally:
            temp_path.unlink()