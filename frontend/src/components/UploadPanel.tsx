import { useState } from "react";

interface Props {
  workspaceId: string | null;
  onUpload: (file: File) => Promise<void>;
}

export default function UploadPanel({ workspaceId, onUpload }: Props) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!workspaceId || !selectedFile) return;

    setLoading(true);
    try {
      await onUpload(selectedFile);
      setSelectedFile(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h3>Upload PDF</h3>

      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => {
          const file = e.target.files?.[0] || null;
          setSelectedFile(file);
        }}
      />

      <button onClick={handleUpload} disabled={!workspaceId || !selectedFile || loading}>
        {loading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}