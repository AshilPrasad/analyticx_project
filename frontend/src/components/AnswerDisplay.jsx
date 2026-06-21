export default function AnswerDisplay({ response }) {
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
          <span className="model-badge">🤖 {response.model || "Gemini"}</span>
        </div>
        <p className="answer-text">{response.answer}</p>
      </div>
    </div>
  );
}
