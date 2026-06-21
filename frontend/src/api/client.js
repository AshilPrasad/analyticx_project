import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_KEY = "analytix_token";

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60s — LLM can be slow
});

// ── Auth token handling ─────────────────────────────────────────────────────────

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

let onUnauthorized = null;
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      clearToken();
      if (onUnauthorized) onUnauthorized();
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const signup = (email, password, name) =>
  api.post("/api/auth/signup", { email, password, name });

export const signin = (email, password) =>
  api.post("/api/auth/signin", { email, password });

export const getMe = () => api.get("/api/auth/me");

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

// ── Config (API key) ──────────────────────────────────────────────────────────

export const getConfig = () => api.get("/api/config/");

export const setGeminiKey = (api_key) =>
  api.post("/api/config/gemini-key", { api_key });

// ── Health ────────────────────────────────────────────────────────────────────

export const checkHealth = () => api.get("/health");
