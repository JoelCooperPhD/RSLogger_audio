#!/usr/bin/env python3
"""
Example master controller for managing multiple audio recorder modules.

This demonstrates how a master logger can control distributed audio
recording modules via MQTT.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import uuid

import asyncio_mqtt as aiomqtt


@dataclass
class RecorderModule:
    """Represents a connected audio recorder module."""
    module_id: str
    state: str = "unknown"
    last_seen: datetime = field(default_factory=datetime.now)
    current_recording: Optional[str] = None
    config: Dict = field(default_factory=dict)


class MasterController:
    """Master controller for managing distributed audio recorders."""
    
    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.base_topic = "rslogger/audio"
        
        # Track connected modules
        self.modules: Dict[str, RecorderModule] = {}
        
        # Pending requests
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Logging
        self.logger = logging.getLogger("MasterController")
        
    async def start(self):
        """Start the master controller."""
        async with aiomqtt.Client(self.mqtt_host, self.mqtt_port) as client:
            self.mqtt_client = client
            
            # Subscribe to all module topics
            await client.subscribe(f"{self.base_topic}/+/status")
            await client.subscribe(f"{self.base_topic}/+/response")
            await client.subscribe(f"{self.base_topic}/+/data")
            
            # Start message handler
            asyncio.create_task(self._handle_messages())
            
            # Keep running
            await asyncio.Event().wait()
    
    async def _handle_messages(self):
        """Handle incoming MQTT messages from modules."""
        async for message in self.mqtt_client.messages:
            try:
                topic_parts = message.topic.value.split('/')
                if len(topic_parts) >= 4:
                    module_id = topic_parts[2]
                    message_type = topic_parts[3]
                    
                    payload = json.loads(message.payload.decode())
                    
                    if message_type == "status":
                        await self._handle_status(module_id, payload)
                    elif message_type == "response":
                        await self._handle_response(module_id, payload)
                    elif message_type == "data":
                        await self._handle_data(module_id, payload)
                        
            except Exception as e:
                self.logger.error(f"Error handling message: {e}")
    
    async def _handle_status(self, module_id: str, status: Dict):
        """Handle status updates from modules."""
        if module_id not in self.modules:
            self.modules[module_id] = RecorderModule(module_id)
            self.logger.info(f"New module discovered: {module_id}")
        
        module = self.modules[module_id]
        module.state = status.get("state", "unknown")
        module.last_seen = datetime.now()
        module.config = status.get("config", {})
        module.current_recording = status.get("recording_id")
        
        self.logger.debug(f"Module {module_id} status: {module.state}")
    
    async def _handle_response(self, module_id: str, response: Dict):
        """Handle command responses from modules."""
        request_id = response.get("request_id")
        if request_id and request_id in self.pending_requests:
            future = self.pending_requests.pop(request_id)
            if not future.done():
                future.set_result(response)
    
    async def _handle_data(self, module_id: str, data: Dict):
        """Handle data events from modules."""
        event = data.get("event")
        if event == "recording_complete":
            self.logger.info(f"Module {module_id} completed recording: {data.get('filename')}")
    
    async def send_command(self, module_id: str, command: str, **kwargs) -> Dict:
        """Send a command to a specific module and wait for response."""
        request_id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Build command payload
        payload = {
            "command": command,
            "request_id": request_id,
            **kwargs
        }
        
        # Send command
        topic = f"{self.base_topic}/{module_id}/command"
        await self.mqtt_client.publish(topic, json.dumps(payload))
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=5.0)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise TimeoutError(f"No response from module {module_id}")
    
    async def start_recording(self, module_id: str, duration: Optional[float] = None,
                            recording_id: Optional[str] = None) -> bool:
        """Start recording on a specific module."""
        try:
            response = await self.send_command(
                module_id, 
                "start",
                duration=duration,
                recording_id=recording_id or datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            return response.get("success", False)
        except Exception as e:
            self.logger.error(f"Failed to start recording on {module_id}: {e}")
            return False
    
    async def stop_recording(self, module_id: str) -> bool:
        """Stop recording on a specific module."""
        try:
            response = await self.send_command(module_id, "stop")
            return response.get("success", False)
        except Exception as e:
            self.logger.error(f"Failed to stop recording on {module_id}: {e}")
            return False
    
    async def start_all_recordings(self, duration: Optional[float] = None) -> Dict[str, bool]:
        """Start recording on all connected modules."""
        recording_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        
        tasks = []
        for module_id in self.modules:
            if self.modules[module_id].state == "idle":
                task = self.start_recording(module_id, duration, recording_id)
                tasks.append((module_id, task))
        
        for module_id, task in tasks:
            results[module_id] = await task
        
        return results
    
    async def stop_all_recordings(self) -> Dict[str, bool]:
        """Stop all active recordings."""
        results = {}
        
        tasks = []
        for module_id in self.modules:
            if self.modules[module_id].state == "recording":
                task = self.stop_recording(module_id)
                tasks.append((module_id, task))
        
        for module_id, task in tasks:
            results[module_id] = await task
        
        return results
    
    def get_module_status(self) -> Dict[str, Dict]:
        """Get status of all modules."""
        return {
            module_id: {
                "state": module.state,
                "last_seen": module.last_seen.isoformat(),
                "current_recording": module.current_recording,
                "online": (datetime.now() - module.last_seen).seconds < 60
            }
            for module_id, module in self.modules.items()
        }


async def demo():
    """Demonstrate master controller functionality."""
    logging.basicConfig(level=logging.INFO)
    
    controller = MasterController()
    
    # Start controller in background
    asyncio.create_task(controller.start())
    
    # Wait for modules to connect
    await asyncio.sleep(2)
    
    # Interactive demo
    while True:
        print("\n--- Master Controller Menu ---")
        print("1. Show module status")
        print("2. Start all recordings (10 seconds)")
        print("3. Start all recordings (continuous)")
        print("4. Stop all recordings")
        print("5. Start specific module")
        print("6. Stop specific module")
        print("0. Exit")
        
        try:
            choice = input("\nChoice: ").strip()
            
            if choice == "1":
                status = controller.get_module_status()
                if not status:
                    print("No modules connected")
                else:
                    for module_id, info in status.items():
                        print(f"\nModule: {module_id}")
                        print(f"  State: {info['state']}")
                        print(f"  Online: {info['online']}")
                        print(f"  Recording: {info['current_recording'] or 'None'}")
            
            elif choice == "2":
                print("Starting 10-second recordings on all modules...")
                results = await controller.start_all_recordings(duration=10)
                for module_id, success in results.items():
                    print(f"  {module_id}: {'Success' if success else 'Failed'}")
            
            elif choice == "3":
                print("Starting continuous recordings on all modules...")
                results = await controller.start_all_recordings()
                for module_id, success in results.items():
                    print(f"  {module_id}: {'Success' if success else 'Failed'}")
            
            elif choice == "4":
                print("Stopping all recordings...")
                results = await controller.stop_all_recordings()
                for module_id, success in results.items():
                    print(f"  {module_id}: {'Success' if success else 'Failed'}")
            
            elif choice == "5":
                module_id = input("Module ID: ").strip()
                duration = input("Duration (seconds, empty for continuous): ").strip()
                duration = float(duration) if duration else None
                
                success = await controller.start_recording(module_id, duration)
                print(f"Start recording: {'Success' if success else 'Failed'}")
            
            elif choice == "6":
                module_id = input("Module ID: ").strip()
                success = await controller.stop_recording(module_id)
                print(f"Stop recording: {'Success' if success else 'Failed'}")
            
            elif choice == "0":
                break
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nExiting...")


if __name__ == "__main__":
    asyncio.run(demo())