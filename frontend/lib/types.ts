export interface Tenant {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  tenant_id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthSession {
  expires_in_seconds: number;
  user: User;
  tenant: Tenant;
}

export interface Collection {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentCollectionInfo {
  id: number;
  name: string;
}

export interface DocumentUploadResponse {
  id: number;
  collection_id: number;
  filename: string;
  source_type: string;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentListItem {
  id: number;
  filename: string;
  source_type: string;
  status: string;
  collection: DocumentCollectionInfo;
  uploaded_at: string | null;
  chunk_count: number;
  ingestion_metadata: Record<string, unknown>;
}

export interface IngestionJobQueuedResponse {
  id: number;
  document_id: number;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestionJobStatusResponse {
  id: number;
  document_id: number;
  status: string;
  error_message: string | null;
  document_status: string;
  chunk_count: number;
  embedding_count: number;
  created_at: string;
  updated_at: string;
}

export interface AnswerCitation {
  collection_id: number;
  collection_name: string;
  document_id: number;
  filename: string;
  chunk_id: number;
  chunk_index: number;
  page_reference: number | number[] | null;
  start_char: number | null;
  end_char: number | null;
  index: number;
  marker: string;
  label: string;
  score: number;
}

export interface RetrievedChunk {
  score: number;
  text: string;
  citation: {
    collection_id: number;
    collection_name: string;
    document_id: number;
    filename: string;
    chunk_id: number;
    chunk_index: number;
    page_reference: number | number[] | null;
    start_char: number | null;
    end_char: number | null;
  };
  metadata_json: Record<string, unknown>;
}

export interface AskResponse {
  question: string;
  collection_id: number | null;
  document_id: number | null;
  document_ids: number[] | null;
  tags: string[] | null;
  source_types: string[] | null;
  top_k: number;
  answer: string;
  confidence: "grounded" | "partial" | "insufficient_evidence";
  insufficient_evidence: boolean;
  missing_information: string[];
  answer_mode: string;
  prompt_version: string;
  citations: AnswerCitation[];
  retrieved_chunks: RetrievedChunk[];
  latency_ms: {
    total_ms: number;
    retrieval_ms: number;
    answer_generation_ms: number;
  };
  providers: {
    embedding_provider: string;
    embedding_model: string;
    llm_provider: string;
    llm_model: string;
  };
}
