"""Configuration management for MQTT-enabled audio recorder."""

import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field


@dataclass
class MQTTConfig:
    """MQTT connection configuration."""
    host: str = "localhost"
    port: int = 1883
    base_topic: str = "rslogger/audio"
    username: Optional[str] = None
    password: Optional[str] = None
    tls_enabled: bool = False
    tls_ca_cert: Optional[str] = None
    keepalive: int = 60
    reconnect_interval: int = 5


@dataclass
class AudioConfig:
    """Audio recording configuration."""
    samplerate: int = 44100
    channels: int = 1
    device: Optional[str] = None
    dtype: str = "float32"
    recording_dir: Path = field(default_factory=lambda: Path("recordings"))
    
    def __post_init__(self):
        """Ensure recording_dir is a Path object."""
        if isinstance(self.recording_dir, str):
            self.recording_dir = Path(self.recording_dir)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["recording_dir"] = str(self.recording_dir)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioConfig":
        """Create from dictionary."""
        if "recording_dir" in data:
            data["recording_dir"] = Path(data["recording_dir"])
        return cls(**data)
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = Path.home() / ".rslogger" / "audio_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AudioConfig":
        """Load configuration from file."""
        if path is None:
            path = Path.home() / ".rslogger" / "audio_config.json"
        
        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)
                return cls.from_dict(data)
        
        return cls()


@dataclass
class ModuleConfig:
    """Complete configuration for MQTT audio recorder module."""
    module_id: str
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    log_level: str = "INFO"
    enable_heartbeat: bool = True
    heartbeat_interval: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "module_id": self.module_id,
            "mqtt": asdict(self.mqtt),
            "audio": self.audio.to_dict(),
            "log_level": self.log_level,
            "enable_heartbeat": self.enable_heartbeat,
            "heartbeat_interval": self.heartbeat_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleConfig":
        """Create from dictionary."""
        mqtt_config = MQTTConfig(**data.get("mqtt", {}))
        audio_config = AudioConfig.from_dict(data.get("audio", {}))
        
        return cls(
            module_id=data["module_id"],
            mqtt=mqtt_config,
            audio=audio_config,
            log_level=data.get("log_level", "INFO"),
            enable_heartbeat=data.get("enable_heartbeat", True),
            heartbeat_interval=data.get("heartbeat_interval", 30)
        )
    
    def save(self, path: Path) -> None:
        """Save configuration to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "ModuleConfig":
        """Load configuration from file."""
        with open(path, "r") as f:
            data = json.load(f)
            return cls.from_dict(data)