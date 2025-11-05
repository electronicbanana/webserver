import json
import os
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSONAS_PATH = os.path.join(BASE_DIR, "personas.json")

def _load_personas() -> dict:
    """Load personas from personas.json. Returns {name: prompt} mapping."""
    default = {
        "Marcus": "You are a helpful assistant.",
        "Claire": "You are soft, nurturing, and empathetic in tone.",
        "Pirate": "Always speak like a pirate, full of nautical slang."
    }
    try:
        with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "personas" in data:
            items = data.get("personas") or []
            out = {}
            for it in items:
                if isinstance(it, dict) and it.get("name") and it.get("prompt"):
                    out[it["name"]] = it["prompt"]
            return out or default
        elif isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()} or default
        elif isinstance(data, list):
            out = {}
            for it in data:
                if isinstance(it, dict) and it.get("name") and it.get("prompt"):
                    out[it["name"]] = it["prompt"]
            return out or default
    except Exception:
        pass
    return default

def _get_persona_prompt(name: Optional[str]) -> str:
    personas = _load_personas()
    if name and name in personas:
        return personas[name]
    return personas.get("Marcus") or "You are a helpful assistant."

