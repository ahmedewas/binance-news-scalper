"""Atomic local state. Never contains API credentials."""
import json
import os
from pathlib import Path


class StateStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return None
        with self.path.open(encoding="utf-8") as handle:
            state = json.load(handle)
        if state.get("version") != 1:
            raise ValueError("Unsupported state format; refusing to discard trading state")
        return state

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
