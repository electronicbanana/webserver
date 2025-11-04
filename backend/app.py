from flask import Flask, request, jsonify # type: ignore
import threading, json, os
from datetime import datetime, timezone
from typing import Optional
UTC = timezone.utc

app = Flask(__name__)

# In-memory chat history (restart clears it)
# Each message: {"id": int, "role": "user"|"server", "text": str, "ts": iso}
MESSAGES = []
CHAT_LOG = "messages.json"
LOCK = threading.Lock()
NEXT_ID = 1

def _now():
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

def _add_message(role, text):
    global NEXT_ID
    with LOCK:
        msg = {"id": NEXT_ID, "role": role, "text": text, "ts": _now()}
        NEXT_ID += 1
        MESSAGES.append(msg)
        return msg

def generate_reply(user_text: str, model: Optional[str] = None) -> str:
    """
    Your 'brain' on the backend. Make this do anything:
    call tools, hit DBs, run ML, etc. For now: a playful echo.
    """
    
    t = user_text.strip()
    if not t:
        return "…"
    
    if t == "/ping":
        return "Pong from the Grid."
    
    if t == "/time":
        return f"Cycle time: {_now()}"
    
    if t == "/clear":
        MESSAGES.clear()
        return "cleared history"
    
    return f"Acknowledged: {t}"

@app.route("/api/messages", methods=["GET"])
def get_messages():
    with LOCK:
        return jsonify(messages=MESSAGES[-200:])  # last 200 for sanity

@app.route("/api/message", methods=["POST"])
def post_message():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").rstrip()
    model = data.get("model") or None
    if not text:
        return jsonify(ok=False, error="Empty message"), 400

    user_msg = {"role": "user", "text": text, "ts": _now()}
    if model:
        user_msg["model"] = model

    reply = generate_reply(text, model)
    server_msg = {"role": "server", "text": reply, "ts": _now()}

    # Save both to JSON
    _append_to_json(user_msg)
    _append_to_json(server_msg)
    
    print(f"User: {text}")
    print(f"Model: {model}")
    print(f"Resp: {reply}")

    return jsonify(ok=True, user=user_msg, reply=server_msg)

if __name__ == "__main__":
    # Dev: run on LAN so phone can access
    app.run(host="0.0.0.0", port=5000, debug=True)
