import type { DocumentItem } from "../types";

interface Props {
  documents: DocumentItem[];
  onDelete: (docId: string) => void;
}

function getStatusClass(status: string) {
  switch (status) {
    case "uploaded":
      return "status-badge status-uploaded";
    case "extracted":
      return "status-badge status-extracted";
    case "ready":
      return "status-badge status-ready";
    case "failed":
      return "status-badge status-failed";
    default:
      return "status-badge";
  }
}

export default function DocumentList({ documents, onDelete }: Props) {
  return (
    <div className="panel">
      <h3>Documents</h3>

      {documents.length === 0 ? (
        <p>No documents in this workspace yet.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((doc, index) => {
            const id = doc.doc_id || doc.id || "";

            return (
              <li
                key={id || `${doc.filename}-${index}`}
                className="doc-item"
              >
                <div className="doc-row">
                  <div>
                    <strong>{doc.filename}</strong>
                    <div>
                      Status:{" "}
                      <span className={getStatusClass(doc.status)}>
                        {doc.status}
                      </span>
                    </div>
                  </div>

                  {id && (
                    <button
                      className="delete-btn"
                      onClick={() => onDelete(id)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}