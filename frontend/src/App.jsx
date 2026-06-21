import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import ChatView from "./components/ChatView";
import AuthScreen from "./components/AuthScreen";
import {
  checkHealth,
  listSessions,
  createSession,
  getSession,
  deleteSession,
  sendMessage,
  listDocuments,
  uploadDocument,
  deleteDocument,
  getConfig,
  setGeminiKey,
  getMe,
  getToken,
  setToken,
  clearToken,
  setUnauthorizedHandler,
} from "./api/client";
import "./index.css";

export default function App() {
  const [authChecking, setAuthChecking] = useState(true);
  const [user, setUser] = useState(null);

  const [apiStatus, setApiStatus] = useState("checking"); // checking | online | degraded | offline
  const [dbMessage, setDbMessage] = useState("");

  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [geminiConfigured, setGeminiConfigured] = useState(true);
  const [savingKey, setSavingKey] = useState(false);
  const [keyError, setKeyError] = useState("");

  const dbAvailable = apiStatus === "online";

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await listDocuments();
      setDocuments(res.data);
    } catch {
      /* ignore */
    }
  }, []);

  const selectSession = useCallback(async (id) => {
    setActiveId(id);
    setSidebarOpen(false);
    try {
      const res = await getSession(id);
      setMessages(res.data.messages || []);
    } catch {
      setMessages([]);
    }
  }, []);

  // Load chat + document data once authenticated
  const loadAppData = useCallback(async () => {
    try {
      const res = await checkHealth();
      if (res.data?.database?.connected) {
        setApiStatus("online");
        setDbMessage("");
        try {
          const cfg = await getConfig();
          setGeminiConfigured(cfg.data?.gemini_configured ?? false);
        } catch {
          setGeminiConfigured(false);
        }
        try {
          const list = (await listSessions()).data;
          setSessions(list);
          if (list.length > 0) selectSession(list[0].id);
        } catch {
          setSessions([]);
        }
        refreshDocuments();
      } else {
        setApiStatus("degraded");
        setDbMessage("PostgreSQL is not running on port 5532. Start the database to enable chat.");
      }
    } catch {
      setApiStatus("offline");
    }
  }, [refreshDocuments, selectSession]);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setSessions([]);
    setMessages([]);
    setActiveId(null);
    setDocuments([]);
  }, []);

  // Validate any existing session on startup
  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    (async () => {
      if (getToken()) {
        try {
          const me = (await getMe()).data;
          setUser(me);
          await loadAppData();
        } catch {
          clearToken();
        }
      }
      setAuthChecking(false);
    })();
  }, [loadAppData]);

  const handleAuthenticated = useCallback(
    async (token, authedUser) => {
      setToken(token);
      setUser(authedUser);
      await loadAppData();
    },
    [loadAppData]
  );

  const handleNewChat = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setSidebarOpen(false);
  }, []);

  const handleDeleteSession = useCallback(
    async (id) => {
      try {
        await deleteSession(id);
        const remaining = sessions.filter((s) => s.id !== id);
        setSessions(remaining);
        if (activeId === id) {
          if (remaining.length > 0) selectSession(remaining[0].id);
          else {
            setActiveId(null);
            setMessages([]);
          }
        }
      } catch {
        /* ignore */
      }
    },
    [sessions, activeId, selectSession]
  );

  const handleSend = useCallback(
    async (question) => {
      if (!question.trim() || sending || !dbAvailable) return;
      setSending(true);

      const optimistic = { id: `tmp-${Date.now()}`, role: "user", content: question };
      setMessages((m) => [...m, optimistic]);

      try {
        let sessionId = activeId;
        if (!sessionId) {
          const created = await createSession();
          sessionId = created.data.id;
          setActiveId(sessionId);
          setSessions((s) => [created.data, ...s]);
        }

        const res = await sendMessage(sessionId, question);
        const { title, message } = res.data;

        setMessages((m) => [...m, message]);
        setSessions((s) =>
          s.map((sess) =>
            sess.id === sessionId
              ? { ...sess, title, updated_at: new Date().toISOString() }
              : sess
          )
        );
      } catch (err) {
        const detail = err.response?.data?.detail || "Something went wrong. Please try again.";
        setMessages((m) => [
          ...m,
          { id: `err-${Date.now()}`, role: "assistant", content: `⚠️ ${detail}`, error: true },
        ]);
      } finally {
        setSending(false);
      }
    },
    [activeId, sending, dbAvailable]
  );

  const handleUpload = useCallback(
    async (file) => {
      if (!file || !dbAvailable) return;
      setUploading(true);
      try {
        await uploadDocument(file);
        await refreshDocuments();
      } catch {
        /* surfaced via UI elsewhere */
      } finally {
        setUploading(false);
      }
    },
    [dbAvailable, refreshDocuments]
  );

  const handleDeleteDoc = useCallback(
    async (name) => {
      try {
        await deleteDocument(name);
        await refreshDocuments();
      } catch {
        /* ignore */
      }
    },
    [refreshDocuments]
  );

  const handleSaveKey = useCallback(async (key) => {
    if (!key.trim()) return;
    setSavingKey(true);
    setKeyError("");
    try {
      const res = await setGeminiKey(key.trim());
      setGeminiConfigured(res.data?.gemini_configured ?? true);
    } catch (err) {
      setKeyError(err.response?.data?.detail || "Could not save the key. Please try again.");
    } finally {
      setSavingKey(false);
    }
  }, []);

  if (authChecking) {
    return (
      <div className="boot-screen">
        <div className="boot-logo">analytix</div>
      </div>
    );
  }

  if (!user) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        sessions={sessions}
        activeId={activeId}
        onSelect={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        documents={documents}
        onUpload={handleUpload}
        onDeleteDoc={handleDeleteDoc}
        uploading={uploading}
        dbAvailable={dbAvailable}
        geminiConfigured={geminiConfigured}
        onSaveKey={handleSaveKey}
        savingKey={savingKey}
        keyError={keyError}
        user={user}
        onLogout={logout}
      />

      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}

      <ChatView
        messages={messages}
        onSend={handleSend}
        sending={sending}
        apiStatus={apiStatus}
        dbMessage={dbMessage}
        hasDocuments={documents.length > 0}
        onOpenSidebar={() => setSidebarOpen(true)}
        geminiConfigured={geminiConfigured}
        onOpenSidebarForKey={() => setSidebarOpen(true)}
      />
    </div>
  );
}
