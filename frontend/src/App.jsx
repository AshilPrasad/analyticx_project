import { useState, useEffect, useCallback } from "react";
import DocumentUpload from "./components/DocumentUpload";
import QuestionInput from "./components/QuestionInput";
import { listDocuments, checkHealth } from "./api/client";
import "./index.css";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [apiStatus, setApiStatus] = useState("checking"); // 'checking' | 'online' | 'degraded' | 'offline'
  const [dbStatusMessage, setDbStatusMessage] = useState("");
  const [activeTab, setActiveTab] = useState("qa"); // 'qa' | 'docs'

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.data);
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    const ping = async () => {
      try {
        const res = await checkHealth();
        const dbConnected = res.data?.database?.connected === true;

        if (dbConnected) {
          setApiStatus("online");
          setDbStatusMessage("");
          fetchDocuments();
        } else {
          setApiStatus("degraded");
          setDbStatusMessage(
            res.data?.database?.message || "Database is not reachable. Start PostgreSQL to enable uploads and Q&A."
          );
          setDocuments([]);
        }
      } catch {
        setApiStatus("offline");
        setDbStatusMessage("");
        setDocuments([]);
      }
    };
    ping();
  }, [fetchDocuments]);

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">🧠</span>
            <div>
              <h1 className="logo-title">DocMind AI</h1>
              <p className="logo-sub">RAG-powered document Q&amp;A</p>
            </div>
          </div>
          <div className="header-right">
            <div className={`status-dot ${apiStatus}`}>
              <span className="dot" />
              <span className="status-label">
                {apiStatus === "checking" && "Connecting…"}
                {apiStatus === "online" && "API Online"}
                {apiStatus === "degraded" && "API Online (DB Offline)"}
                {apiStatus === "offline" && "API Offline"}
              </span>
            </div>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost"
            >
              API Docs ↗
            </a>
          </div>
        </div>
      </header>

      {/* ── Hero Banner ── */}
      <div className="hero">
        <div className="hero-inner">
          <p className="hero-tag">Powered by Llama 3 · pgvector · sentence-transformers</p>
          <h2 className="hero-headline">
            Ask anything about your documents
          </h2>
          <p className="hero-desc">
            Upload PDFs or text files, then ask questions in plain English.
            DocMind retrieves the most relevant passages and generates precise answers.
          </p>

          {/* Stats bar */}
          <div className="stats-bar">
            <div className="stat">
              <span className="stat-num">{documents.length}</span>
              <span className="stat-label">Documents</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-num">
                {documents.reduce((a, d) => a + d.chunk_count, 0)}
              </span>
              <span className="stat-label">Chunks Indexed</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-num">384</span>
              <span className="stat-label">Embedding Dims</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-num">Llama 3</span>
              <span className="stat-label">LLM Model</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Mobile tab switcher ── */}
      <div className="tab-bar">
        <button
          className={`tab-btn ${activeTab === "qa" ? "active" : ""}`}
          onClick={() => setActiveTab("qa")}
        >
          💬 Ask
        </button>
        <button
          className={`tab-btn ${activeTab === "docs" ? "active" : ""}`}
          onClick={() => setActiveTab("docs")}
        >
          📁 Documents {documents.length > 0 && `(${documents.length})`}
        </button>
      </div>

      {/* ── Main layout ── */}
      <main className="main-layout">
        {/* Left panel — Q&A (primary) */}
        <div className={`panel-left ${activeTab === "qa" ? "tab-active" : ""}`}>
          {apiStatus === "offline" ? (
            <div className="offline-banner">
              🔴 Cannot connect to the API at <code>http://localhost:8000</code>.
              Make sure the backend is running: <code>python run.py</code>
            </div>
          ) : apiStatus === "degraded" ? (
            <div className="degraded-banner">
              🟠 Backend is running, but database is unavailable.
              <br />
              <code>{dbStatusMessage}</code>
            </div>
          ) : (
            <QuestionInput hasDocuments={documents.length > 0} />
          )}
        </div>

        {/* Right panel — Document manager */}
        <div className={`panel-right ${activeTab === "docs" ? "tab-active" : ""}`}>
          <DocumentUpload
            documents={documents}
            onRefresh={fetchDocuments}
            dbAvailable={apiStatus === "online"}
          />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        <p>
          Built with FastAPI · PostgreSQL · pgvector · sentence-transformers ·
          Groq (Llama 3) · React
        </p>
      </footer>
    </div>
  );
}
