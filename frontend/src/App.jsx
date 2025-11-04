import "./App.css";
import { useEffect, useRef, useState } from "react";

export default function App() {
  // Simple hash-based routing: chat | settings | info
  const [route, setRoute] = useState(() => (location.hash.replace(/^#\/?/, "") || "chat"));
  useEffect(() => {
    const onHash = () => setRoute(location.hash.replace(/^#\/?/, "") || "chat");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (to) => { location.hash = to; };

  return (
    <>
      <SiteNav route={route} navigate={navigate} />
      {route === "settings" ? (
        <SettingsPage />
      ) : route === "info" ? (
        <InfoPage />
      ) : (
        <ChatPage />
      )}
    </>
  );
}

function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);
  const MODELS = ["Marcus", "Agent1", "Agent2"];
  const [model, setModel] = useState(MODELS[0]);

  // Fetch history on load
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/messages");
        const data = await res.json();
        setMessages(data.messages || []);
      } catch {
        // ignore for demo
      }
    })();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function send() {
    const raw = text.trim();
    if (!raw || sending) return;
    setSending(true);

    // Optimistic user bubble
    const tempUser = {
      id: Date.now(),
      role: "user",
      text: raw,
      ts: new Date().toISOString(),
      _temp: true
    };
    setMessages((m) => [...m, tempUser]);
    setText("");

    try {
      const res = await fetch("/api/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: raw, model })
      });
      const data = await res.json();

      if (!data.ok) throw new Error(data.error || "send failed");

      // Replace temp user msg with server-confirmed one + add reply
      setMessages((m) => {
        const withoutTemp = m.filter((x) => !x._temp);
        return [...withoutTemp, data.user, data.reply];
      });
    } catch (e) {
      // mark temp as failed
      setMessages((m) =>
        m.map((x) =>
          x._temp ? { ...x, text: `${x.text}  ❌ (failed)` } : x
        )
      );
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="page">
      <div className="grid-bg" />
      <TopRightMenu models={MODELS} selected={model} onChoose={setModel} />

      <div className="center">
        <header className="header">
          <h1 className="title">END OF LINE</h1>
          <p className="subtitle">A tiny Tron-style messenger (React ↔ Flask)</p>
        </header>

        <div className="chat-panel">
          <div className="messages" ref={listRef}>
            {messages.map((m) => (
              <Message key={m.id} role={m.role} text={m.text} ts={m.ts} />
            ))}
          </div>

          <div className="composer">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Speak, program… (Enter to send)"
              rows={2}
            />
            <button className="send-btn" onClick={send} disabled={sending}>
              {sending ? "Transmitting…" : "Transmit"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Message({ role, text, ts }) {
  const isUser = role === "user";
  return (
    <div className={`bubble-row ${isUser ? "right" : "left"}`}>
      <div className={`bubble ${isUser ? "bubble-user" : "bubble-server"}`}>
        <div className="bubble-text">{text}</div>
        <div className="bubble-ts">{new Date(ts).toLocaleTimeString()}</div>
      </div>
    </div>
  );
}

function TopRightMenu({ models = [], selected, onChoose }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    }
    function onEsc(e) { if (e.key === "Escape") setOpen(false); }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  return (
    <div className="top-right-menu" ref={ref}>
      <button
        className="menu-btn"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Choose model"
      >
        {selected ? `Model: ${selected}` : "Models"}
      </button>
      {open && (
        <div className="menu-popover" role="menu">
          {models.map((m) => (
            <button
              key={m}
              className="menu-item"
              role="menuitemradio"
              aria-checked={selected === m}
              onClick={() => { onChoose(m); setOpen(false); }}
            >
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SiteNav({ route, navigate }) {
  return (
    <nav className="site-nav" aria-label="Primary">
      <div className="nav-inner">
        <div className="brand">Grid</div>
        <div className="nav-list">
          <a className={`nav-link ${route === 'chat' ? 'active' : ''}`} href="#chat" onClick={(e)=>{e.preventDefault(); navigate('chat');}}>Chat</a>
          <a className={`nav-link ${route === 'settings' ? 'active' : ''}`} href="#settings" onClick={(e)=>{e.preventDefault(); navigate('settings');}}>Settings</a>
          <a className={`nav-link ${route === 'info' ? 'active' : ''}`} href="#info" onClick={(e)=>{e.preventDefault(); navigate('info');}}>Info</a>
        </div>
      </div>
    </nav>
  );
}

function SettingsPage() {
  return (
    <div className="page">
      <div className="grid-bg" />
      <div className="center">
        <header className="header">
          <h1 className="title">SETTINGS</h1>
          <p className="subtitle">Placeholder controls for future configuration</p>
        </header>
        <div className="chat-panel" style={{maxWidth: 680, margin: '0 auto'}}>
          <p>Coming soon: theme toggle, server URL, and agent options.</p>
          <p style={{opacity: 0.8}}>Tip: Use the “Models” menu on Chat to pick an agent per message.</p>
        </div>
      </div>
    </div>
  );
}

function InfoPage() {
  return (
    <div className="page">
      <div className="grid-bg" />
      <div className="center">
        <header className="header">
          <h1 className="title">INFO</h1>
          <p className="subtitle">About this demo</p>
        </header>
        <div className="chat-panel" style={{maxWidth: 680, margin: '0 auto', textAlign: 'left'}}>
          <p>
            A tiny Tron-style messenger: React (Vite) frontend talking to a Flask backend.
            The backend echoes with a playful reply and logs messages to <code>backend/messages.json</code>.
          </p>
          <p>
            Dev commands: <code>npm run dev</code> in <code>frontend/</code> and <code>python backend/app.py</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
