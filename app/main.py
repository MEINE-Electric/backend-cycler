from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from threading import Lock, Thread
from typing import List, Dict, Any
import asyncio
import json
import time

from cycler.mqtt import MQTTClient
from cycler.sequencer import Sequencer
from cycler.influx import InfluxWriter
from cycler.store import Sequence
from peripherals.heartbeat import Heartbeat

# -------------------- App --------------------

app = FastAPI(title="Local Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Globals --------------------

SEQUENCER: dict[str, Sequencer] = {}
COMMANDS: dict[str, Sequence] = {}
ROWS: dict[str, Dict] = {}
MQTT: dict[str, MQTTClient] = {}
DATA: dict[str, dict] = {}
STATUS: dict[str, dict] = {}

INFLUX = InfluxWriter(
    url="http://localhost:8086",
    token="WbOEczaLxeXnus-UNgj8IpUN1oS4SNqMP52DznTTYmC62I9fafSlcgWYIgdZYQ1h3kFHPmGpSmERjUKT_Vq2Rg==",
    org="meine",
    bucket="experiments",
)

HEARTBEAT_MQTT = Heartbeat()

clients: set[WebSocket] = set()
clients_lock = asyncio.Lock()

# -------------------- Startup Init --------------------

N = 4 # setups
C = 2  # channels

for i in range(N):
    for j in range(C):
        NODE_ID = str(i + 1)
        CYCLER_ID = str(j + 1)
        SETUP_ID = NODE_ID + CYCLER_ID

        mqtt = MQTTClient(
            setup_id=SETUP_ID,
            broker="192.168.10.1",
            topic=f"raspberry/{NODE_ID}/cycler/{CYCLER_ID}",
            influx=INFLUX,
        )

        mqtt.start()

        SEQUENCER[SETUP_ID] = Sequencer(mqtt)
        MQTT[SETUP_ID] = mqtt

for i in range(1,N+1):
    for j in range(1, C+1):
        DATA[f"{i}{j}"] = None

HEARTBEAT_MQTT.start()

# -------------------- REST Routes --------------------

@app.post("/set/{SETUP_ID}")
def set_command(SETUP_ID: str, DATA: Dict[str, Any]):

    commands = DATA["commands"]
    rows = DATA["rows"]

    
    if commands is None or rows is None:
        raise HTTPException(400, "Invalid payload structure")

    if SETUP_ID not in SEQUENCER:
        raise HTTPException(404, "Invalid SETUP_ID")

    seq = COMMANDS.get(SETUP_ID)
    if not seq:
        seq = Sequence()
        COMMANDS[SETUP_ID] = seq
    seq.set(commands)

    ROWS[SETUP_ID] = rows
    
    return {"status": "ok"}

@app.post("/start/{SETUP_ID}")
def start_cycler(SETUP_ID: str):
    if SETUP_ID not in SEQUENCER:
        raise HTTPException(404, "Invalid SETUP_ID")

    if SETUP_ID not in COMMANDS:
        raise HTTPException(400, "No sequence configured")

    Thread(
        target=SEQUENCER[SETUP_ID].run,
        args=(COMMANDS[SETUP_ID],),
        daemon=True,
    ).start()

    return {"status": "started"}

@app.get("/rows/{SETUP_ID}")
def get_rows(SETUP_ID: str):
    if SETUP_ID not in ROWS:
        
        rows = [
            {
                "action": "Select",
                "voltage": "",
                "current": "",
                "time": "",
                "repeat": "",
                "target": "",
            }
            for _ in range(20)
        ]

        return rows

    return ROWS[SETUP_ID]

@app.get("/heartbeat")
def get_heartbeats():
    return HEARTBEAT_MQTT.peripherals

# -------------------- WebSocket --------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    async with clients_lock:
        clients.add(ws)

    try:
        while True:
            await asyncio.sleep(60)  # keep connection alive
    finally:
        async with clients_lock:
            clients.discard(ws)

async def broadcaster():
    while True:
        dead = []

        for setup_id, mqtt in MQTT.items():
            DATA[setup_id] = mqtt.latest_readings
            STATUS[setup_id] = mqtt.status

        msg = json.dumps({
            "t": time.time(),
            "data": DATA,
            "status": STATUS
        })

        async with clients_lock:
            for ws in clients:
                try:
                    await ws.send_text(msg)
                except:
                    dead.append(ws)

            for ws in dead:
                clients.discard(ws)

        await asyncio.sleep(0.5)

# -------------------- Lifecycle --------------------

@app.on_event("startup")
async def start_broadcast():
    asyncio.create_task(broadcaster())

@app.on_event("shutdown")
def shutdown():
    for mqtt in MQTT.values():
        mqtt.stop()

    HEARTBEAT_MQTT.stop()
    INFLUX.close()