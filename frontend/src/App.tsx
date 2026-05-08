import { useEffect, useState } from "react";
import "./index.css";
import WorkspaceSidebar from "./components/WorkspaceSidebar";
import UploadPanel from "./components/UploadPanel";
import DocumentList from "./components/DocumentList";
import ChatPanel from "./components/ChatPanel";
import {
  createWorkspace,
  getDocuments,
  getWorkspaces,
  uploadPdf,
  extractDocument,
  chunkDocument,
  deleteDocument,
} from "./api/client";
import type { DocumentItem, Workspace } from "./types";

export default function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMessage, setProcessingMessage] = useState("");

  const loadWorkspaces = async () => {
    try {
      const data = await getWorkspaces();
      console.log("workspaces response:", data);

      const items = data.workspaces || data || [];
      setWorkspaces(items);

      if (!selectedWorkspaceId && items.length > 0) {
        setSelectedWorkspaceId(items[0].id);
      }
    } catch (error) {
      console.error("Failed to load workspaces:", error);
    }
  };

  const loadDocuments = async (workspaceId: string) => {
    try {
      const data = await getDocuments(workspaceId);
      console.log("documents response:", data);

      const items = data.documents || data || [];
      setDocuments(items);
    } catch (error) {
      console.error("Failed to load documents:", error);
      setDocuments([]);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, []);

  useEffect(() => {
    if (selectedWorkspaceId) {
      loadDocuments(selectedWorkspaceId);
    }
  }, [selectedWorkspaceId]);

  const handleCreateWorkspace = async (name: string) => {
    try {
      const created = await createWorkspace(name);
      console.log("created workspace response:", created);

      await loadWorkspaces();

      if (created?.workspace_id) {
        setSelectedWorkspaceId(created.workspace_id);
      }
    } catch (error) {
      console.error("Failed to create workspace:", error);
    }
  };

  const handleUpload = async (file: File) => {
    if (!selectedWorkspaceId) return;

    try {
      setIsProcessing(true);
      setProcessingMessage("Uploading PDF...");

      const uploaded = await uploadPdf(selectedWorkspaceId, file);
      console.log("upload response:", uploaded);

      const docId = uploaded?.doc_id;
      if (!docId) {
        throw new Error("Upload succeeded but no doc_id returned");
      }

      await loadDocuments(selectedWorkspaceId);

      setProcessingMessage("Extracting text...");
      await extractDocument(docId);
      await loadDocuments(selectedWorkspaceId);

      setProcessingMessage("Building chunks and index...");
      await chunkDocument(docId);
      await loadDocuments(selectedWorkspaceId);

      setProcessingMessage("Done.");
    } catch (error) {
      console.error("Failed to upload/process PDF:", error);
      setProcessingMessage("Processing failed.");
      await loadDocuments(selectedWorkspaceId);
    } finally {
      setTimeout(() => {
        setIsProcessing(false);
        setProcessingMessage("");
      }, 800);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedWorkspaceId) return;

    try {
      await deleteDocument(docId);
      await loadDocuments(selectedWorkspaceId);
    } catch (error) {
      console.error("Failed to delete document:", error);
    }
  };

  return (
    <div className="app-layout">
      <WorkspaceSidebar
        workspaces={workspaces}
        selectedWorkspaceId={selectedWorkspaceId}
        onSelectWorkspace={setSelectedWorkspaceId}
        onCreateWorkspace={handleCreateWorkspace}
      />

      <main className="main-content">
        <h1>PDF Chat Assistant</h1>

        <UploadPanel
          workspaceId={selectedWorkspaceId}
          onUpload={handleUpload}
        />

        {isProcessing && (
          <div className="panel processing-banner">
            <div className="spinner" />
            <span>{processingMessage}</span>
          </div>
        )}

        <DocumentList
          documents={documents}
          onDelete={handleDeleteDocument}
        />

        <ChatPanel workspaceId={selectedWorkspaceId} />
      </main>
    </div>
  );
}