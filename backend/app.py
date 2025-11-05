from flask import Flask, request, jsonify # type: ignore
from flask import Response
import threading, json, os, re
import json as _json
from datetime import datetime, timezone
from typing import Optional

from commands import _run_command
from personas import _load_personas as p_load_personas, _get_persona_prompt as p_get_persona_prompt
from storage import (
    _load_chat_file as s_load_chat_file,
    _write_chat_file as s_write_chat_file,
    _add_and_persist as s_add_and_persist,
    _clear_chat as s_clear_chat,
    _list_chats as s_list_chats,
    _chat_path as s_chat_path,
    _append_to_commands_json as s_append_cmd,
    _add_command_message as s_add_cmd_msg,
    _clear_commands as s_clear_commands,
    COMMANDS_LOG as s_COMMANDS_LOG,
)

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

UTC = timezone.utc
app = Flask(__name__)

# (moved state and storage helpers to storage.py)

# Endpoint for local model (e.g., Ollama)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_CHAT_URL = os.environ.get("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")

def generate_reply(user_text: str, model: Optional[str] = None) -> str:
    """
    Your 'brain' on the backend. Make this do anything:
    call tools, hit DBs, run ML, etc. For now: a playful echo.
    """
    
    t = user_text.strip()
    if not t:
        return "…"
    
    elif t.startswith("/"):
        return _run_command(t)

    else:
        return f"Acknowledged: {t}"

@app.route("/api/messages", methods=["GET", "DELETE"])
def get_messages():
    chat = request.args.get("chat")
    if request.method == "DELETE":
        s_clear_chat(chat)
        return jsonify(ok=True)
    state = s_load_chat_file(chat)
    return jsonify(messages=state["messages"][-200:], meta=state["meta"])  # last 200 for sanity

@app.route("/api/personas", methods=["GET"])
def get_personas():
    mapping = p_load_personas()
    items = [{"name": k, "prompt": v} for k, v in mapping.items()]
    # Keep a consistent order (by name)
    items.sort(key=lambda x: x["name"].lower())
    return jsonify(personas=items)

@app.route("/api/commands", methods=["GET", "DELETE"])
def commands_collection():
    if request.method == "DELETE":
        s_clear_commands()
        return jsonify(ok=True)
    # Read commands log (user/server entries)
    data = []
    if os.path.exists(s_COMMANDS_LOG):
        try:
            with open(s_COMMANDS_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []
    return jsonify(messages=data[-200:])

@app.route("/api/command", methods=["POST"])
def post_command():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").rstrip()
    if not text:
        return jsonify(ok=False, error="Empty command"), 400
    # Record the command conversation separately (not mixed with chat history)
    user_msg = s_add_cmd_msg("user", text)
    s_append_cmd(user_msg)
    # Dispatch using existing command handler
    reply_text = _run_command(text)
    server_msg = s_add_cmd_msg("server", reply_text)
    s_append_cmd(server_msg)
    return jsonify(ok=True, user=user_msg, reply=server_msg)

@app.route("/api/message", methods=["POST"])
def post_message():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").rstrip()
    model = data.get("model") or None
    chat = data.get("chat") or None
    if not text:
        return jsonify(ok=False, error="Empty message"), 400

    # If this is a clear command, wipe the chat before recording messages
    if text.strip() == "/clear":
        s_clear_chat(chat)

    user_msg = s_add_and_persist(chat, "user", text, model)

    reply = generate_reply(text, model)
    server_msg = s_add_and_persist(chat, "server", reply, model)

    # Logging
    print(f"User: {text}")
    print(f"Model: {model}")
    print(f"Resp: {reply}")

    return jsonify(ok=True, user=user_msg, reply=server_msg)


@app.route("/api/stream", methods=["GET"])
def stream_message():
    """Server-Sent Events stream that proxies to the model.

    Query params:
      - text: user input
      - model: optional model name
    """
    text = (request.args.get("text") or "").strip()
    chat = request.args.get("chat") or None
    src = (request.args.get("src") or "").strip().lower()
    no_commands = (request.args.get("no_commands") or "").strip().lower() in {"1", "true", "yes"}
    # Resolve model: query > chat meta > default
    q_model = request.args.get("model") or None
    if q_model:
        model = q_model
    else:
        state_for_model = _load_chat_file(chat)
        meta_for_model = state_for_model.get("meta") or {}
        model = meta_for_model.get("model") or "llama3.2:3b"
    if not text:
        return jsonify(error="missing text"), 400

    # Slash-commands handled locally (non-streaming from model) unless suppressed by src/no_commands
    if text.startswith("/") and not (src == "chat" or no_commands):
        # Handle per-chat clear
        if text.strip() == "/clear":
            s_clear_chat(chat)
        reply = generate_reply(text, model)

        def once():
            yield f"data: {{\"delta\": {_json.dumps(reply)} }}\n\n"
            yield "event: done\ndata: {}\n\n"

        return Response(once(), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # Record user message to selected chat
    s_add_and_persist(chat, "user", text, model)

    def _history_as_chat_messages():
        state = s_load_chat_file(chat)
        history = state["messages"]
        meta = state.get("meta") or {}
        persona_name = meta.get("persona")
        system_prompt = p_get_persona_prompt(persona_name)
        msgs = []
        # System prompt from persona
        msgs.append({"role": "system", "content": system_prompt})
        for m in history[-200:]:  # safety cap
            role = m.get("role")
            content = m.get("text", "")
            if not content:
                continue
            if role == "user":
                msgs.append({"role": "user", "content": content})
            elif role == "server":
                msgs.append({"role": "assistant", "content": content})
        return msgs

    def sse():
        acc: list[str] = []
        # Prefer Ollama chat API so it has full conversation context
        payload_chat = {"model": model, "messages": _history_as_chat_messages(), "stream": True}
        if requests is None:
            yield f"event: error\ndata: {{\"error\": \"requests not installed\"}}\n\n"
            yield "event: done\ndata: {}\n\n"
            return
        try:
            # Try chat endpoint first
            with requests.post(OLLAMA_CHAT_URL, json=payload_chat, stream=True, timeout=60) as r:  # type: ignore[attr-defined]
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = _json.loads(line)
                    except Exception:
                        continue
                    # Ollama /api/chat stream frames contain chunk["message"]["content"]
                    delta = None
                    msg = chunk.get("message")
                    if isinstance(msg, dict):
                        delta = msg.get("content")
                    # Fallback: support /api/generate format if needed
                    if delta is None and "response" in chunk:
                        delta = chunk.get("response")
                    if delta:
                        acc.append(delta)
                        yield f"data: {{\"delta\": {_json.dumps(delta)} }}\n\n"
                    if chunk.get("done"):
                        break
        except Exception as e:
            yield f"event: error\ndata: {{\"error\": {_json.dumps(str(e))} }}\n\n"
        finally:
            final = "".join(acc)
            if final:
                _add_and_persist(chat, "server", final, model)
            yield "event: done\ndata: {}\n\n"

    return Response(sse(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/chats", methods=["GET", "POST"])
def chats_collection():
    if request.method == "GET":
        return jsonify(chats=s_list_chats())
    data = request.get_json(silent=True) or {}
    model = (data.get("model") or "").strip() or "llama3.2:3b"
    title = (data.get("title") or "").strip()
    persona = (data.get("persona") or "").strip() or None
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    model_slug = re.sub(r"[^-_.a-zA-Z0-9]", "-", model)
    fname = f"{model_slug}_{ts}.json"
    path = s_chat_path(fname)
    meta = {
        # Use provided title or a light placeholder (model); will be renamed after first user message
        "title": title or model,
        "model": model,
        "persona": persona,
        "created": datetime.now(UTC).isoformat().replace("+00:00", "Z")
    }
    s_write_chat_file(path, meta, [])
    return jsonify(chat=fname, meta=meta), 201

@app.route("/api/chats/<chat>", methods=["GET", "PATCH", "DELETE"])
def chat_item(chat):
    if request.method == "GET":
        state = s_load_chat_file(chat)
        return jsonify(chat=_safe_chat_filename(chat), meta=state["meta"], messages=state["messages"])
    # PATCH: update meta (title/model)
    if request.method == "PATCH":
        data = request.get_json(silent=True) or {}
        state = s_load_chat_file(chat)
        meta = dict(state["meta"])
        if "model" in data and data["model"]:
            meta["model"] = data["model"]
        if "title" in data and data["title"]:
            meta["title"] = data["title"]
        if "persona" in data:
            meta["persona"] = data["persona"] or None
        s_write_chat_file(state["path"], meta, state["messages"])
        return jsonify(ok=True, meta=meta)
    # DELETE: remove chat file entirely
    path = s_chat_path(chat)
    try:
        if os.path.exists(path) and path.endswith('.json'):
            os.remove(path)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

if __name__ == "__main__":
    # Dev: run on LAN so phone can access
    app.run(host="0.0.0.0", port=5000, debug=True)
