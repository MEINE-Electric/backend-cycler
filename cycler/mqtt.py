import json
import threading
import asyncio
import paho.mqtt.client as mqtt

class MQTTClient:
    def __init__(self, setup_id, broker, topic ,influx=None):
        self.broker = broker
        self.topic = topic
        self.influx = influx
        self.setup_id = setup_id
        self.node_id = setup_id[0]
        self.cycler_id = setup_id[1]
        self.measurement = "test2"
        
        self.ack = threading.Event()
        self.ack.set()
        self.data_changed = asyncio.Event()

        self.client = mqtt.Client(client_id=self.setup_id)
        self.latest_heartbeat = {}
        self.latest_readings = {}
        self.status = {}

    def start(self):
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.broker, 1883, 60)
        self.client.loop_start()

    def publish(self, subtopic, payload):
        self.ack.clear()
        self.client.publish(
            f"{self.topic}/{subtopic}",
            json.dumps(payload),
            qos=1,
        )

        if self.influx:
            self.influx.write(self.measurement, payload, self.node_id, self.cycler_id, self.setup_id)

    # ---------- Callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe(self.topic + "/#", qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())

            if msg.topic.endswith("/ack") and data.get("feedback") == "ACK":
                if self.influx:
                    self.influx.write(self.measurement, {"event": "ACK"}, self.node_id, self.cycler_id, self.setup_id)
                
                self.ack.set()

            if msg.topic.endswith("/data") and self.influx:
                if data['state'] != 'IDLE':
                    self.influx.write(self.measurement, data, self.node_id, self.cycler_id, self.setup_id)

                self.latest_readings = data
                self.data_changed.set()

        except Exception as e:
            print(f"[MQTT] error: {e}")

    def stop(self):
        print("[MQTT] stopping...")
        self.client.loop_stop()  # stop background loop
        self.client.disconnect()