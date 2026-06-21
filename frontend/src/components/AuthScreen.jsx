import { useState } from "react";
import { signin, signup } from "../api/client";

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("signin"); // 'signin' | 'signup'
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError("");
    setLoading(true);
    try {
      const res =
        mode === "signup"
          ? await signup(email.trim(), password, name.trim())
          : await signin(email.trim(), password);
      onAuthenticated(res.data.access_token, res.data.user);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-brand">analytix</div>
        <p className="auth-tagline">RAG-powered document Q&amp;A</p>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === "signin" ? "active" : ""}`}
            onClick={() => { setMode("signin"); setError(""); }}
          >
            Sign in
          </button>
          <button
            className={`auth-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => { setMode("signup"); setError(""); }}
          >
            Sign up
          </button>
        </div>

        <form className="auth-form" onSubmit={submit}>
          {mode === "signup" && (
            <input
              className="auth-input"
              type="text"
              placeholder="Name (optional)"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
          <input
            className="auth-input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder={mode === "signup" ? "Password (min 6 characters)" : "Password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            required
          />

          {error && <p className="auth-error">{error}</p>}

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="auth-switch">
          {mode === "signin" ? "New here? " : "Already have an account? "}
          <button
            className="auth-switch-btn"
            onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); }}
          >
            {mode === "signin" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
