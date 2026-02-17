from .influx import InfluxWriter
from .mqtt import MQTTClient
from .sequencer import Sequencer 
from .store import Sequence 

SETUP_ID = input("Enter ID: ")

NODE_ID = SETUP_ID[0]
CYCLER_ID = SETUP_ID[1]

COMMANDS = [    
    ### --- 16 hours discharge with 0.25A till 0.6V
    {
        "command": "CONFIG",
        "config_updates": {
            "psu_voltage_set": 0.0,
            "psu_current_set": 0.0,
            "psu_ovp_limit": 20.0,
            "psu_ocp_limit": 20.0,
            "load_voltage_set": 2.5,
            "load_current_set": 0.25,
            "load_channel": CYCLER_ID,
            "load_mode": "CURR",
        },
    },
    {
        "command": "DISCHARGE",
        "discharge_time_limit": 10,
        "discharge_threshold": -0.6,
    },

    ### --- 6 hours charge with 0.5A till 2.5V
    {
        "command": "CONFIG",
        "config_updates": {
            "psu_voltage_set": 2.5,
            "psu_current_set": 0.5,
            "psu_ovp_limit": 20.0,
            "psu_ocp_limit": 20.0,
            "load_voltage_set": 0.0,
            "load_current_set": 0.0,
            "load_channel": CYCLER_ID,
            "load_mode": "CURR",
        },
    },
    {
        "command": "CHARGE",
        "charge_time_limit": 21600,
        "charge_threshold": 12.5,
    },

    ### --- Repeat the previous for 3 times
    {
        "command": "GOTO",
        "target": 0,
        "repeat": 2
    }
]

commands = Sequence()
commands.set(COMMANDS)

influx = InfluxWriter(
    url="http://localhost:8086",
    token="WbOEczaLxeXnus-UNgj8IpUN1oS4SNqMP52DznTTYmC62I9fafSlcgWYIgdZYQ1h3kFHPmGpSmERjUKT_Vq2Rg==",
    org="meine",
    bucket="experiments",
    node_id=NODE_ID,
    cycler_id=CYCLER_ID,
    setup_id=SETUP_ID,
)

mqtt = MQTTClient(
    broker="192.168.10.1",
    topic=f"raspberry/{NODE_ID}/cycler/{CYCLER_ID}",
    influx=influx,
)

mqtt.start()
sequencer = Sequencer(mqtt)

try:
    sequencer.run(commands)
    pass
finally:
    mqtt.stop()     # stop MQTT background thread cleanly
    influx.close()  # flush and close Influx client
