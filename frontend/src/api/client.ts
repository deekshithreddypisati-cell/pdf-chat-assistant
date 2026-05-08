import axios from "axios";

const API_BASE = "https://pdf-chat-backend-jccs.onrender.com";

export const api = axios.create({
  baseURL: API_BASE,
});

export async function getWorkspaces() {
  const res = await api.get("/workspaces");
  return res.data;
}

export async function createWorkspace(name: string) {
  const res = await api.post(
    `/workspaces?name=${encodeURIComponent(name)}`
  );
  return res.data;
}

export async function getDocuments(workspaceId: string) {
  const res = await api.get(
    `/workspaces/${workspaceId}/documents`
  );
  return res.data;
}

export async function uploadPdf(
  workspaceId: string,
  file: File
) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post(
    `/workspaces/${workspaceId}/upload`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return res.data;
}

export async function extractDocument(docId: string) {
  const res = await api.post(`/documents/${docId}/extract`);
  return res.data;
}

export async function chunkDocument(docId: string) {
  const res = await api.post(`/documents/${docId}/chunk`);
  return res.data;
}

export async function deleteDocument(docId: string) {
  const res = await api.delete(`/documents/${docId}`);
  return res.data;
}