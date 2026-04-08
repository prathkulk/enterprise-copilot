import type {
  AskResponse,
  AuthSession,
  Collection,
  DocumentListItem,
  DocumentUploadResponse,
  IngestionJobQueuedResponse,
  IngestionJobStatusResponse,
} from "@/lib/types";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: JsonValue;
  formData?: FormData;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export async function registerUser(payload: {
  tenant_name: string;
  full_name: string;
  email: string;
  password: string;
}): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function loginUser(payload: {
  email: string;
  password: string;
}): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/login", {
    method: "POST",
    body: payload,
  });
}

export async function fetchSession(): Promise<AuthSession | null> {
  return request<AuthSession | null>("/api/auth/session");
}

export async function logoutUser(): Promise<void> {
  await request<void>("/api/auth/logout", { method: "POST" });
}

export async function fetchCollections(): Promise<Collection[]> {
  return request<Collection[]>("/api/backend/collections");
}

export async function createCollection(payload: {
  name: string;
  description?: string | null;
}): Promise<Collection> {
  return request<Collection>("/api/backend/collections", {
    method: "POST",
    body: payload,
  });
}

export async function fetchDocuments(collectionId: number): Promise<DocumentListItem[]> {
  return request<DocumentListItem[]>(`/api/backend/collections/${collectionId}/documents`);
}

export async function uploadDocument(
  collectionId: number,
  file: File,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.set("file", file);
  return request<DocumentUploadResponse>(`/api/backend/collections/${collectionId}/documents/upload`, {
    method: "POST",
    formData,
  });
}

export async function ingestDocument(
  documentId: number,
): Promise<IngestionJobQueuedResponse> {
  return request<IngestionJobQueuedResponse>(`/api/backend/documents/${documentId}/ingest`, {
    method: "POST",
  });
}

export async function fetchJobStatus(jobId: number): Promise<IngestionJobStatusResponse> {
  return request<IngestionJobStatusResponse>(`/api/backend/jobs/${jobId}`);
}

export async function deleteDocument(documentId: number): Promise<void> {
  await request<void>(`/api/backend/documents/${documentId}`, {
    method: "DELETE",
  });
}

export async function askCollection(payload: {
  question: string;
  collection_id: number;
  top_k?: number;
}): Promise<AskResponse> {
  return request<AskResponse>("/api/backend/ask", {
    method: "POST",
    body: {
      question: payload.question,
      collection_id: payload.collection_id,
      top_k: payload.top_k ?? 5,
    },
  });
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers,
    body,
    cache: "no-store",
    credentials: "same-origin",
  });

  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function extractErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    const { detail } = payload;

    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            return String(entry.msg);
          }
          return JSON.stringify(entry);
        })
        .join(" ");
    }
  } catch {
    // Fall through to status text.
  }

  return response.statusText || "Request failed.";
}
