import json
from pathlib import Path
from typing import Any

PATH = Path("data/state.json")


def load_state() -> dict[str, dict[str, Any]]:
    if not PATH.exists():
        return {}
    return json.loads(PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, dict[str, Any]]) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")