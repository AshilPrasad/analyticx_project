import { useState } from "react";

export default function AnswerDisplay({ response }) {
  const [expandedSource, setExpandedSource] = useState(null);

  return (
    <div className="answer-container">
      {/* Question echo */}
      <div className="question-bubble">
        <span className="bubble-label">You asked</span>
        <p>{response.question}</p>
      </div>

      {/* Answer */}
      <div className="answer-bubble">
        <div className="answer-header">
          <span className="model-badge">🤖 llama3-8b-8192 via Groq</span>
        </div>
        <p className="answer-text">{response.answer}</p>
      </div>

      {/* Sources */}
      {response.sources && response.sources.length > 0 && (
        <div className="sources-section">
          <h4 className="sources-title">📎 Sources Used</h4>
          <div className="source-list">
            {response.sources.map((src, idx) => (
              <div key={idx} className="source-card">
                <div
                  className="source-header"
                  onClick={() =>
                    setExpandedSource(expandedSource === idx ? null : idx)
                  }
                >
                  <div className="source-left">
                    <span className="source-icon">📄</span>
                    <span className="source-name">{src.document_name}</span>
                    <span className="similarity-badge">
                      {(src.similarity * 100).toFixed(1)}% match
                    </span>
                  </div>
                  <span className="expand-icon">
                    {expandedSource === idx ? "▲" : "▼"}
                  </span>
                </div>

                {expandedSource === idx && (
                  <div className="source-content">
                    <p>{src.content}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
