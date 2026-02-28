import time
from copy import deepcopy
from .store import Sequence

class Sequencer:
    """
    Executes a command sequence and communicates with hardware via MQTT.
    Pure control logic. No UI / visualization concerns.
    """

    def __init__(self, mqtt_client):
        self.mqtt = mqtt_client
        self.running = False
        self.current_step = 0

    def run(self, commands: Sequence):
        """
        Run the command sequence.
        Blocks until sequence completes.
        """
        self.running = True
        self.current_step = 0
        self.commands = commands 
        
        goto_repeats = {}

        while self.current_step < self.commands.len() and self.running:
            self.mqtt.status["state"] = "running"
            self.mqtt.status["step"] = self.current_step
            self.mqtt.status["goto"] = goto_repeats

            # Wait for hardware readiness
            self.mqtt.ack.wait()

            cmd = self.commands.get(self.current_step)
            self.commands.print_all(self.current_step)
            
            name = cmd["command"]

            print(f"[SEQ] {self.current_step:02d} → {name}")

            if name == "CONFIG":
                self._handle_config(cmd)

            elif name in ("CHARGE", "DISCHARGE", "HOLD"):
                self._handle_state(cmd)

            elif name == "REST":
                self._handle_rest(cmd)

            elif name == "GOTO":
                if self._handle_goto(cmd, goto_repeats):
                    continue  # jump occurred
            else:
                raise ValueError(f"Unknown command: {name}")

            self.current_step += 1

        self.running = False

        self.mqtt.status["state"] = "idle"
        self.mqtt.status["step"] = self.current_step
        self.mqtt.status["goto"] = goto_repeats

        print("[SEQ] END")

    # ------------------------
    # Command handlers
    # ------------------------
    def _handle_config(self, cmd: dict):
        self.mqtt.publish("config", cmd)
        self.mqtt.ack.set()
        print("[SEQ] CONFIG applied")

    def _handle_state(self, cmd: dict):
        self.mqtt.publish("commands", cmd)
        print(f"[SEQ] {cmd['command']} running")

    def _handle_rest(self, cmd: dict):
        self.mqtt.publish("commands", cmd)
        print("[SEQ] REST STATE")

    def _handle_goto(self, cmd: dict, goto_repeats: dict) -> bool:
        """
        Returns True if a jump occurred, False otherwise.
        """
        idx = int(self.current_step)
        target = cmd["target"]
        max_repeats = cmd["repeat"]

        # Initialize repeat counter
        if idx not in goto_repeats:
            goto_repeats[idx] = max_repeats

        goto_repeats[idx] -= 1

        if goto_repeats[idx] > 0:
            print(
                f"[SEQ] GOTO → {target} "
                f"(repeats left: {goto_repeats[idx]})"
            )
            self.current_step = target*2
            return True

        # Done repeating
        del goto_repeats[idx]
        self.mqtt.ack.set()
        print("[SEQ] GOTO finished")
        return False
    
    # ------------------------
    # Control Handlers
    # ------------------------
    def _handle_stop(self):
        self.mqtt.publish("commands", {"command": "STOP"})
        self.running = False
        print("[SEQ] STOP command sent")

    def _handle_pause(self):
        self.mqtt.publish("commands", {"command": "PAUSE"})
        self.running = False
        print("[SEQ] PAUSE command sent")

    def _handle_resume(self):
        self.mqtt.publish("commands", {"command": "RESUME"})
        self.running = True
        print("[SEQ] RESUME command sent")

    def _handle_skip(self):
        self.mqtt.publish("commands", {"command": "SKIP"})
        print("[SEQ] SKIP command sent")
    
    # ------------------------
    # Control hooks (optional)
    # ------------------------
    def stop(self):
        """Safely stop execution after current step."""
        self.mqtt.publish("stop", cmd)
        self.running = False