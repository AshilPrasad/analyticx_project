import { useState, useRef, useEffect } from "react";

const SUGGESTIONS = [
  "Summarise the key points of my documents.",
  "What are the main topics covered?",
  "List any important facts or figures.",
];

export default function ChatView({
  messages,
  onSend,
  sending,
  apiStatus,
  dbMessage,
  hasDocuments,
  onOpenSidebar,
  geminiConfigured,
  onOpenSidebarForKey,
}) {
  const [input, setInput] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const submit = (e) => {
    e?.preventDefault();
    if (!input.trim() || sending) return;
    onSend(input.trim());
    setInput("");
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const needsKey = apiStatus === "online" && !geminiConfigured;
  const disabled = apiStatus !== "online" || needsKey;

  return (
    <main className="chat-main">
      <header className="chat-topbar">
        <button className="menu-btn" onClick={onOpenSidebar} aria-label="Open menu">
          ☰
        </button>
        <span className="chat-title">analytix</span>
        <span className={`conn-dot ${apiStatus}`} title={apiStatus} />
      </header>

      <div className="chat-scroll">
        {apiStatus === "offline" && (
          <div className="state-banner error">
            🔴 Cannot reach the API at <code>http://localhost:8000</code>. Start the backend with{" "}
            <code>python run.py</code>.
          </div>
        )}
        {apiStatus === "degraded" && (
          <div className="state-banner warn">
            🟠 {dbMessage} <br />
            Run <code>docker compose up -d db</code>, then restart the backend.
          </div>
        )}
        {needsKey && (
          <div className="state-banner warn">
            🔑 No Gemini API key set. Open the menu and add your key under{" "}
            <strong>Gemini API Key</strong> to start chatting.{" "}
            <button className="inline-link-btn" onClick={onOpenSidebarForKey}>
              Add key
            </button>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-logo">✦</div>
            <h1 className="empty-title">How can I help you today?</h1>
            <p className="empty-sub">
              Ask anything about your uploaded documents. analytix retrieves the most relevant
              passages and answers with Google Gemini.
            </p>
            {!hasDocuments && apiStatus === "online" && (
              <p className="empty-hint">
                Tip: open the menu and upload a document first for grounded answers.
              </p>
            )}
            {hasDocuments && (
              <div className="suggestion-grid">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="suggestion-card"
                    disabled={disabled}
                    onClick={() => onSend(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="messages">
            {messages.map((m) => (
              <div key={m.id} className={`msg-row ${m.role}`}>
                <div className={`msg-bubble ${m.role} ${m.error ? "error" : ""}`}>
                  {m.content}
                </div>
              </div>
            ))}
            {sending && (
              <div className="msg-row assistant">
                <div className="msg-bubble assistant typing">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <form className="composer" onSubmit={submit}>
        <textarea
          className="composer-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            needsKey
              ? "Add your Gemini API key to start chatting…"
              : apiStatus !== "online"
              ? "Connect the database to start chatting…"
              : "Message analytix…"
          }
          rows={1}
          disabled={disabled || sending}
        />
        <button
          type="submit"
          className="composer-send"
          disabled={!input.trim() || sending || disabled}
          aria-label="Send"
        >
          ➤
        </button>
      </form>
      <p className="composer-foot">analytix can make mistakes. Verify important information.</p>
    </main>
  );
}
