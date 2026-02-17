import json
import threading
import paho.mqtt.client as mqtt
import asyncio

class Heartbeat:
    def __init__(self):
        self.broker = "192.168.10.1"
        self.topic = "raspberry/+/heartbeat"
        self.client = mqtt.Client(client_id = "Heartbeat Monitor")
        self.peripherals = {}
        self.data_changed = asyncio.Event()

    def start(self):
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker, 1883, 60)
        self.client.loop_start()

# ---------- Callbacks ----------
    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe(self.topic, qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())

            if msg.topic.endswith("/heartbeat"):
                node_id = msg.topic.split("/")[1]
                fields = {
                    "load": data.get('id').get('load'),
                    "supply_1": data.get('id').get("supply_1"),
                    "supply_2": data.get('id').get("supply_2"),
                    "module_1": data.get('id').get("module_1"),
                    "module_2": data.get('id').get("module_2")
                } 
                self.peripherals[node_id] = fields
                self.data_changed.set()

        except Exception as e:
            print(f"[MQTT] error: {e}")

    def stop(self):
        print("[MQTT] stopping...")
        self.client.loop_stop()  # stop background loop
        self.client.disconnect()