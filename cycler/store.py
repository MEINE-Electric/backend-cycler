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
