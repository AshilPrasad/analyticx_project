import { useState, useCallback } from "react";
import { uploadDocument, deleteDocument } from "../api/client";

function friendlyError(err) {
  const detail = err.response?.data?.detail ?? "";
  if (!detail) return "Upload failed. Please try again.";
  // Strip raw Python exception class names from server error messages
  if (detail.toLowerCase().includes("database unavailable")) {
    return "Database is not connected. Start PostgreSQL and restart the backend.";
  }
  if (detail.length > 200) return detail.slice(0, 200) + "…";
  return detail;
}

export default function DocumentUpload({ documents, onRefresh, dbAvailable = true }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const handleUpload = useCallback(async (file) => {
    if (!file || !dbAvailable) return;
    setUploading(true);
    setUploadStatus(null);
    try {
      const res = await uploadDocument(file);
      setUploadStatus({
        type: "success",
        msg: `✅ "${res.data.document_name}" ingested — ${res.data.chunks_created} chunks created.`,
      });
      onRefresh();
    } catch (err) {
      setUploadStatus({
        type: "error",
        msg: `❌ ${friendlyError(err)}`,
      });
    } finally {
      setUploading(false);
    }
  }, [onRefresh, dbAvailable]);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      if (!dbAvailable) return;
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload, dbAvailable]
  );

  const handleDelete = async (name) => {
    try {
      await deleteDocument(name);
      setUploadStatus({ type: "success", msg: `🗑️ "${name}" removed.` });
      onRefresh();
    } catch {
      setUploadStatus({ type: "error", msg: "Failed to delete document." });
    }
  };

  return (
    <div className="upload-panel">
      <h2 className="section-title">
        <span className="icon">📁</span> Knowledge Base
      </h2>

      {/* DB unavailable — show friendly notice instead of upload zone */}
      {!dbAvailable ? (
        <div className="db-unavailable-notice">
          <div className="db-unavailable-icon">🗄️</div>
          <p className="db-unavailable-title">Database not connected</p>
          <p className="db-unavailable-desc">
            Start PostgreSQL (port 5532) and restart the backend to enable document uploads and Q&amp;A.
          </p>
          <code className="db-unavailable-cmd">docker compose up -d db</code>
        </div>
      ) : (
        /* Drop Zone */
        <div
          id="drop-zone"
          className={`drop-zone ${isDragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
        >
          <div className="drop-zone-content">
            {uploading ? (
              <>
                <div className="spinner" />
                <p>Ingesting document…</p>
              </>
            ) : (
              <>
                <div className="upload-icon">⬆️</div>
                <p className="drop-label">Drag & drop a file here</p>
                <p className="drop-sub">or</p>
                <label className="btn btn-primary" htmlFor="file-input">
                  Browse Files
                </label>
                <input
                  id="file-input"
                  type="file"
                  accept=".txt,.pdf"
                  style={{ display: "none" }}
                  onChange={(e) => handleUpload(e.target.files[0])}
                />
                <p className="drop-hint">Supports .txt and .pdf · Max 10 MB</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Status message */}
      {uploadStatus && (
        <div className={`status-msg ${uploadStatus.type}`}>
          {uploadStatus.msg}
        </div>
      )}

      {/* Document list */}
      <div className="doc-list">
        <h3 className="doc-list-title">Ingested Documents</h3>
        {documents.length === 0 ? (
          <p className="empty-hint">No documents yet. Upload one above.</p>
        ) : (
          <ul>
            {documents.map((doc) => (
              <li key={doc.document_name} className="doc-item">
                <div className="doc-info">
                  <span className="doc-icon">📄</span>
                  <div>
                    <p className="doc-name">{doc.document_name}</p>
                    <p className="doc-meta">{doc.chunk_count} chunks</p>
                  </div>
                </div>
                <button
                  className="btn btn-danger-sm"
                  onClick={() => handleDelete(doc.document_name)}
                  title="Delete document"
                >
                  🗑️
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
