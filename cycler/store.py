from threading import Lock
from copy import deepcopy

class Sequence:
    def __init__(self):
        self._lock = Lock()
        self._sequence = []

    def set(self, commands: list[dict]):
        with self._lock:
            self._sequence = deepcopy(commands)

    def get(self, index: int) -> dict | None:
        with self._lock:
            if index >= len(self._sequence):
                return None
            return deepcopy(self._sequence[index])

    def len(self):
        with self._lock:
            return len(self._sequence)

    def print_all(self, index: int = None):
        with self._lock:
            for i, cmd in enumerate(self._sequence):
                if index is None:
                    print(f"Index {i}: {cmd.get('command', 'N/A')}")
                elif i == index:
                    print(f"\033[93mIndex {i}: {cmd.get('command', 'N/A')} <-- current step\033[0m")
                else:
                    print(f"Index {i}: {cmd.get('command', 'N/A')}")
