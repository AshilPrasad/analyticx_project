import { useState } from "react";
import { askQuestion } from "../api/client";
import AnswerDisplay from "./AnswerDisplay";

export default function QuestionInput({ hasDocuments }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await askQuestion(question.trim());
      setResponse(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const suggestedQuestions = [
    "What is the main topic of the document?",
    "Summarise the key points.",
    "What conclusions are drawn?",
    "List any important facts or figures.",
  ];

  return (
    <div className="qa-panel">
      <h2 className="section-title">
        <span className="icon">💬</span> Ask a Question
      </h2>

      {!hasDocuments && (
        <div className="notice">
          ⚠️ Upload at least one document before asking questions.
        </div>
      )}

      {/* Suggested questions */}
      {hasDocuments && !response && (
        <div className="suggestions">
          <p className="suggestions-label">Try asking:</p>
          <div className="suggestion-chips">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                className="chip"
                onClick={() => setQuestion(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input form */}
      <form className="qa-form" onSubmit={handleSubmit}>
        <div className="input-wrapper">
          <textarea
            id="question-input"
            className="question-textarea"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your documents…"
            rows={3}
            disabled={loading || !hasDocuments}
          />
          <button
            id="submit-question"
            type="submit"
            className={`btn btn-primary send-btn ${loading ? "loading" : ""}`}
            disabled={!question.trim() || loading || !hasDocuments}
          >
            {loading ? <span className="spinner-sm" /> : "Ask →"}
          </button>
        </div>
        <p className="input-hint">Press Enter to submit · Shift+Enter for new line</p>
      </form>

      {/* Error */}
      {error && (
        <div className="status-msg error">❌ {error}</div>
      )}

      {/* Answer */}
      {response && <AnswerDisplay response={response} />}
    </div>
  );
}
