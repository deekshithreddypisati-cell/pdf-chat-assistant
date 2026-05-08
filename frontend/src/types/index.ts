export interface Workspace {
  id: string;
  name: string;
  created_at?: string;
}

export interface DocumentItem {
  id?: string;
  doc_id?: string;
  filename: string;
  status: string;
  uploaded_at?: string;
  page_count?: number;
  storage_path?: string;
}

export interface Citation {
  doc_id: string;
  page_num: number;
}

export interface EvidenceQuote {
  doc_id: string;
  page_num: number;
  quote: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  evidence_quotes?: EvidenceQuote[];
}