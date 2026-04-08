"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useEffectEvent, useState } from "react";
import { CollectionSwitcher } from "@/components/collection-switcher";
import { DashboardShell } from "@/components/dashboard-shell";
import { StatusPill } from "@/components/status-pill";
import { useAuth } from "@/components/auth-provider";
import {
  ApiError,
  deleteDocument,
  fetchCollections,
  fetchDocuments,
  fetchJobStatus,
  ingestDocument,
} from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Collection, DocumentListItem, IngestionJobStatusResponse } from "@/lib/types";

export default function DocumentsPage() {
  const params = useParams<{ collectionId: string }>();
  const collectionId = Number(params.collectionId);
  const { session } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [jobStates, setJobStates] = useState<Record<number, IngestionJobStatusResponse>>({});
  const [busyDocumentIds, setBusyDocumentIds] = useState<number[]>([]);

  const selectedCollection = collections.find((item) => item.id === collectionId) ?? null;
  const refreshPageDataEvent = useEffectEvent(() => { void refreshPageData(); });

  async function refreshPageData() {
    setLoading(true);
    try {
      const [c, d] = await Promise.all([fetchCollections(), fetchDocuments(collectionId)]);
      setCollections(c);
      setDocuments(d);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.detail : "Couldn't load documents right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session || Number.isNaN(collectionId)) return;
    refreshPageDataEvent();
  }, [collectionId, session]);

  async function handleIngest(documentId: number) {
    setBusyDocumentIds((c) => [...c, documentId]);
    setError(null);
    try {
      const queued = await ingestDocument(documentId);
      await pollJob(documentId, queued.id);
      await refreshPageData();
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.detail : "Couldn't process this document right now.");
    } finally {
      setBusyDocumentIds((c) => c.filter((id) => id !== documentId));
    }
  }

  async function pollJob(documentId: number, jobId: number) {
    while (true) {
      const status = await fetchJobStatus(jobId);
      setJobStates((c) => ({ ...c, [documentId]: status }));
      if (status.status === "indexed" || status.status === "failed") return;
      await new Promise((r) => setTimeout(r, 1200));
    }
  }

  async function handleDelete(documentId: number) {
    if (!window.confirm("Remove this document? This can't be undone.")) return;
    try {
      await deleteDocument(documentId);
      setDocuments((c) => c.filter((d) => d.id !== documentId));
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.detail : "Couldn't delete that document right now.");
    }
  }

  return (
    <DashboardShell
      title="Documents"
      description="Process your files to make them searchable."
      collectionName={selectedCollection?.name}
      collectionId={collectionId}
    >
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {collections.length > 1 ? (
              <CollectionSwitcher
                collections={collections}
                selectedCollectionId={selectedCollection?.id ?? null}
                routeBuilder={(id) => `/collections/${id}/documents`}
              />
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => void refreshPageData()} className="button-secondary !py-2 text-sm">
              Refresh
            </button>
            <Link href={`/collections/${collectionId}/upload`} className="button-secondary !py-2 text-sm">
              Upload files
            </Link>
            <Link href={`/collections/${collectionId}/ask`} className="button-primary !py-2 text-sm">
              Ask questions
            </Link>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="panel rounded-[1.6rem] p-6 text-[var(--muted)]">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="panel rounded-[1.6rem] p-10 text-center">
            <h4 className="text-xl font-semibold">No documents here yet</h4>
            <p className="mt-2 text-[var(--muted)]">Upload a file first, then come back to process it.</p>
            <Link href={`/collections/${collectionId}/upload`} className="button-primary mt-5 inline-flex">
              Upload a file
            </Link>
          </div>
        ) : (
          <div className="grid gap-4">
            {documents.map((document) => {
              const jobState = jobStates[document.id];
              const busy = busyDocumentIds.includes(document.id);
              return (
                <article key={document.id} className="panel rounded-[1.6rem] p-5">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusPill status={jobState?.document_status ?? document.status} />
                        <span className="text-xs uppercase text-[var(--muted)]">{document.source_type.toUpperCase()}</span>
                      </div>
                      <h4 className="mt-2 truncate text-xl font-semibold">{document.filename}</h4>
                      <div className="mt-3 flex flex-wrap gap-4 text-sm text-[var(--muted)]">
                        <span>Uploaded {formatDate(document.uploaded_at)}</span>
                        <span>{jobState?.chunk_count ?? document.chunk_count} sections</span>
                        {(jobState?.embedding_count ?? 0) > 0 ? (
                          <span className="text-[var(--success)]">Processed</span>
                        ) : null}
                      </div>
                      {jobState?.error_message ? (
                        <p className="mt-2 text-sm text-[var(--danger)]">{jobState.error_message}</p>
                      ) : null}
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        onClick={() => void handleIngest(document.id)}
                        disabled={busy}
                        className="button-primary !py-2 text-sm"
                      >
                        {busy ? "Processing..." : "Process"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDelete(document.id)}
                        className="button-secondary !py-2 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}