import os
import re
import json
import threading
from datetime import datetime, timezone
from typing import Optional

UTC = timezone.utc

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_DIR = os.path.join(BASE_DIR, "chats")
os.makedirs(CHAT_DIR, exist_ok=True)

# Legacy single-chat fallback file
CHAT_LOG = os.path.join(BASE_DIR, "messages.json")

# Separate commands log
COMMANDS_LOG = os.path.join(BASE_DIR, "commands.json")

# In-memory counters and lock
LOCK = threading.Lock()
MESSAGES = []
NEXT_ID = 1
NEXT_CMD_ID = 1

def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")

def _append_to_json(entry):
    with LOCK:
        data = []
        if os.path.exists(CHAT_LOG):
            try:
                with open(CHAT_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []
        data.append(entry)
        with open(CHAT_LOG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

def _append_to_commands_json(entry):
    with LOCK:
        data = []
        if os.path.exists(COMMANDS_LOG):
            try:
                with open(COMMANDS_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = []
        data.append(entry)
        with open(COMMANDS_LOG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

def _add_message(role, text):
    global NEXT_ID
    with LOCK:
        msg = {"id": NEXT_ID, "role": role, "text": text, "ts": _now()}
        NEXT_ID += 1
        MESSAGES.append(msg)
        return msg

def _add_command_message(role, text):
    global NEXT_CMD_ID
    with LOCK:
        msg = {"id": NEXT_CMD_ID, "role": role, "text": text, "ts": _now()}
        NEXT_CMD_ID += 1
        return msg

def _safe_chat_filename(name: str) -> str:
    base = os.path.basename(name or "")
    if not base:
        base = "default.json"
    if not base.endswith(".json"):
        base += ".json"
    base = re.sub(r"[^-_.a-zA-Z0-9]", "-", base)
    return base

def _chat_path(chat: Optional[str]) -> str:
    if not chat:
        return CHAT_LOG
    base = _safe_chat_filename(chat)
    if base == os.path.basename(CHAT_LOG):
        return CHAT_LOG
    return os.path.join(CHAT_DIR, base)

def _load_chat_file(chat: Optional[str]):
    path = _chat_path(chat)
    if not os.path.exists(path):
        return {"meta": {}, "messages": [], "next_id": 1, "path": path}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    if isinstance(data, dict):
        meta = data.get("meta") or {}
        messages = data.get("messages") or []
    else:
        meta = {}
        messages = data
    out = []
    next_id = 1
    for m in messages:
        if not isinstance(m, dict):
            continue
        e = dict(m)
        if isinstance(e.get("id"), int) and e["id"] > 0:
            eid = e["id"]
        else:
            eid = next_id
            e["id"] = eid
        out.append(e)
        next_id = max(next_id, eid + 1)
    return {"meta": meta, "messages": out, "next_id": next_id, "path": path}

def _write_chat_file(path: str, meta: dict, messages: list):
    payload = {"meta": meta, "messages": messages}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

def _quick_title(source: str, fallback_model: Optional[str] = None) -> str:
    if not source:
        return (fallback_model or "New Chat")
    s = source.strip()
    if s.startswith("/"):
        return (fallback_model or "New Chat")
    s = re.sub(r"\s+", " ", s)
    m = re.split(r"(?<=[.!?])\s", s, maxsplit=1)
    first = m[0] if m else s
    words = first.split()
    if len(words) > 8:
        first = " ".join(words[:8])
    first = first.strip('\"\'\-:,; ')
    if len(first) > 40:
        cut = first[:40].rstrip()
        sp = cut.rfind(" ")
        if sp >= 20:
            cut = cut[:sp]
        first = cut + "…"
    if first:
        first = first[0].upper() + first[1:]
    return first or (fallback_model or "New Chat")

def _add_and_persist(chat: Optional[str], role: str, text: str, model: Optional[str] = None) -> dict:
    state = _load_chat_file(chat)
    meta = state["meta"]
    messages = state["messages"]
    msg = {"id": state["next_id"], "role": role, "text": text, "ts": _now()}
    if model:
        msg["model"] = model
        meta = dict(meta)
        meta["model"] = model
    if role == "user" and len(messages) == 0:
        t = _quick_title(text, meta.get("model"))
        meta = dict(meta)
        meta["title"] = t
    messages.append(msg)
    _write_chat_file(state["path"], meta, messages)
    return msg

def _clear_chat(chat: Optional[str]):
    state = _load_chat_file(chat)
    _write_chat_file(state["path"], state.get("meta") or {}, [])

def _list_chats():
    items = []
    if os.path.exists(CHAT_LOG):
        try:
            st = os.stat(CHAT_LOG)
            items.append({
                "chat": os.path.basename(CHAT_LOG),
                "path": CHAT_LOG,
                "title": "default",
                "model": None,
                "created": None,
                "updated": datetime.fromtimestamp(st.st_mtime, UTC).isoformat().replace("+00:00", "Z")
            })
        except Exception:
            pass
    for name in sorted(os.listdir(CHAT_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CHAT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        meta = {}
        if isinstance(data, dict):
            meta = data.get("meta") or {}
        st = os.stat(path)
        items.append({
            "chat": name,
            "title": meta.get("title") or name,
            "model": meta.get("model"),
            "created": meta.get("created"),
            "updated": datetime.fromtimestamp(st.st_mtime, UTC).isoformat().replace("+00:00", "Z")
        })
    return items

def _clear_all():
    global MESSAGES, NEXT_ID
    with LOCK:
        MESSAGES = []
        NEXT_ID = 1
        try:
            with open(CHAT_LOG, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        except Exception:
            pass

def _clear_commands():
    with LOCK:
        try:
            with open(COMMANDS_LOG, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
        except Exception:
            pass

def _load_messages_into_memory():
    global MESSAGES, NEXT_ID
    data = []
    if os.path.exists(CHAT_LOG):
        try:
            with open(CHAT_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    loaded = []
    next_id = 1
    for entry in data:
        if not isinstance(entry, dict):
            continue
        e = dict(entry)
        if isinstance(e.get("id"), int) and e["id"] > 0:
            eid = e["id"]
        else:
            eid = next_id
            e["id"] = eid
        loaded.append(e)
        next_id = max(next_id, eid + 1)
    with LOCK:
        MESSAGES = loaded
        NEXT_ID = next_id

def _load_commands_into_memory():
    global NEXT_CMD_ID
    data = []
    if os.path.exists(COMMANDS_LOG):
        try:
            with open(COMMANDS_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    next_id = 1
    for entry in data:
        if isinstance(entry, dict) and isinstance(entry.get("id"), int) and entry["id"] > 0:
            next_id = max(next_id, entry["id"] + 1)
    with LOCK:
        NEXT_CMD_ID = next_id

# Initialize counters on import
_load_messages_into_memory()
_load_commands_into_memory()

