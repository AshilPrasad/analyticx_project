import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — LLM can be slow
});

// ── Documents ─────────────────────────────────────────────────────────────────

export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/api/documents/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const listDocuments = () => api.get("/api/documents/");

export const deleteDocument = (name) =>
  api.delete(`/api/documents/${encodeURIComponent(name)}`);

// ── Chat sessions ─────────────────────────────────────────────────────────────

export const createSession = () => api.post("/api/chat/sessions");

export const listSessions = () => api.get("/api/chat/sessions");

export const getSession = (id) => api.get(`/api/chat/sessions/${id}`);

export const deleteSession = (id) => api.delete(`/api/chat/sessions/${id}`);

export const sendMessage = (sessionId, question, top_k = 5) =>
  api.post(`/api/chat/sessions/${sessionId}/messages`, { question, top_k });

// ── Health ────────────────────────────────────────────────────────────────────

export const checkHealth = () => api.get("/health");
