import { useState } from "react";

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function Sidebar({
  open,
  sessions,
  activeId,
  onSelect,
  onNewChat,
  onDeleteSession,
  documents,
  onUpload,
  onDeleteDoc,
  uploading,
  dbAvailable,
}) {
  const [showDocs, setShowDocs] = useState(false);

  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <div className="sidebar-header">
        <span className="brand">analytix</span>
      </div>

      <button className="new-chat-btn" onClick={onNewChat} disabled={!dbAvailable}>
        <span className="plus">＋</span> New chat
      </button>

      <div className="session-list">
        <p className="session-list-label">Chats</p>
        {sessions.length === 0 ? (
          <p className="session-empty">No conversations yet.</p>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              className={`session-item ${s.id === activeId ? "active" : ""}`}
              onClick={() => onSelect(s.id)}
            >
              <span className="session-icon">💬</span>
              <span className="session-title" title={s.title}>
                {s.title}
              </span>
              <span className="session-date">{formatDate(s.updated_at)}</span>
              <button
                className="session-delete"
                title="Delete chat"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(s.id);
                }}
              >
                🗑
              </button>
            </div>
          ))
        )}
      </div>

      {/* Knowledge Base */}
      <div className="kb-section">
        <button className="kb-toggle" onClick={() => setShowDocs((v) => !v)}>
          <span>📁 Knowledge Base {documents.length > 0 && `(${documents.length})`}</span>
          <span>{showDocs ? "▾" : "▸"}</span>
        </button>

        {showDocs && (
          <div className="kb-body">
            <label className={`kb-upload ${!dbAvailable || uploading ? "disabled" : ""}`}>
              {uploading ? "Uploading…" : "⬆ Upload .txt / .pdf"}
              <input
                type="file"
                accept=".txt,.pdf"
                disabled={!dbAvailable || uploading}
                style={{ display: "none" }}
                onChange={(e) => {
                  if (e.target.files[0]) onUpload(e.target.files[0]);
                  e.target.value = "";
                }}
              />
            </label>

            {documents.length === 0 ? (
              <p className="kb-empty">No documents. Upload to enable answers.</p>
            ) : (
              <ul className="kb-list">
                {documents.map((d) => (
                  <li key={d.document_name} className="kb-item">
                    <span className="kb-name" title={d.document_name}>
                      📄 {d.document_name}
                    </span>
                    <button
                      className="kb-delete"
                      title="Remove document"
                      onClick={() => onDeleteDoc(d.document_name)}
                    >
                      🗑
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <span className="retention-note">Chats auto-delete after 90 days</span>
      </div>
    </aside>
  );
}
