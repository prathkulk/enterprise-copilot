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
import type {
  Collection,
  DocumentListItem,
  IngestionJobStatusResponse,
} from "@/lib/types";

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
  const refreshPageDataEvent = useEffectEvent(() => {
    void refreshPageData();
  });

  async function refreshPageData() {
    setLoading(true);
    try {
      const [collectionsResponse, documentsResponse] = await Promise.all([
        fetchCollections(),
        fetchDocuments(collectionId),
      ]);
      setCollections(collectionsResponse);
      setDocuments(documentsResponse);
      setError(null);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't load the documents yet.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session || Number.isNaN(collectionId)) {
      return;
    }

    refreshPageDataEvent();
  }, [collectionId, session]);

  async function handleIngest(documentId: number) {
    setBusyDocumentIds((current) => [...current, documentId]);
    setError(null);

    try {
      const queued = await ingestDocument(documentId);
      await pollJob(documentId, queued.id);
      await refreshPageData();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't start indexing yet.",
      );
    } finally {
      setBusyDocumentIds((current) => current.filter((item) => item !== documentId));
    }
  }

  async function pollJob(documentId: number, jobId: number) {
    while (true) {
      const status = await fetchJobStatus(jobId);
      setJobStates((current) => ({ ...current, [documentId]: status }));

      if (status.status === "indexed" || status.status === "failed") {
        return;
      }

      await new Promise((resolve) => {
        window.setTimeout(resolve, 1200);
      });
    }
  }

  async function handleDelete(documentId: number) {
    const confirmed = window.confirm("Delete this document from the collection?");
    if (!confirmed) {
      return;
    }

    try {
      await deleteDocument(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't delete that document yet.",
      );
    }
  }

  return (
    <DashboardShell
      title="Index documents"
      description="This is where your uploaded files turn into something the assistant can actually search and quote back to you."
    >
      <div className="space-y-6">
        <section className="panel rounded-[1.8rem] p-6">
          <div className="grid gap-4 lg:grid-cols-[1fr_auto_auto] lg:items-end">
            <div>
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
                Step 3
              </p>
              <h3 className="mt-3 text-2xl font-semibold">
                {selectedCollection?.name ?? "Loading collection..."}
              </h3>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                Start indexing when you&apos;re ready. The app will extract the text, split it into chunks, embed it, and mark the document as searchable when it&apos;s done.
              </p>
            </div>

            {collections.length > 0 ? (
              <CollectionSwitcher
                collections={collections}
                selectedCollectionId={selectedCollection?.id ?? null}
                routeBuilder={(nextCollectionId) => `/collections/${nextCollectionId}/documents`}
              />
            ) : null}

            <div className="flex flex-wrap gap-3 lg:justify-end">
              <button type="button" onClick={() => void refreshPageData()} className="button-secondary">
                Refresh
              </button>
              <Link href={`/collections/${collectionId}/ask`} className="button-primary">
                Go to questions
              </Link>
            </div>
          </div>

          {error ? (
            <div className="mt-5 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
              {error}
            </div>
          ) : null}
        </section>

        {loading ? (
          <div className="panel rounded-[1.8rem] p-6 text-[var(--muted)]">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="panel rounded-[1.8rem] p-8 text-center">
            <h4 className="text-xl font-semibold">Nothing to index yet</h4>
            <p className="mt-3 text-[var(--muted)]">
              Upload a file first, then come back here when you want to make it searchable.
            </p>
            <div className="mt-6">
              <Link href={`/collections/${collectionId}/upload`} className="button-primary">
                Go to upload
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid gap-4">
            {documents.map((document) => {
              const jobState = jobStates[document.id];
              const busy = busyDocumentIds.includes(document.id);

              return (
                <article key={document.id} className="panel rounded-[1.8rem] p-6">
                  <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
                    <div className="max-w-3xl">
                      <div className="flex flex-wrap items-center gap-3">
                        <StatusPill status={jobState?.document_status ?? document.status} />
                        <span className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                          {document.source_type}
                        </span>
                      </div>
                      <h4 className="mt-4 text-2xl font-semibold">{document.filename}</h4>
                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        <Metric label="Uploaded" value={formatDate(document.uploaded_at)} />
                        <Metric label="Chunks" value={String(jobState?.chunk_count ?? document.chunk_count)} />
                        <Metric label="Embeddings" value={String(jobState?.embedding_count ?? 0)} />
                      </div>
                      {jobState?.error_message ? (
                        <p className="mt-4 text-sm text-[var(--danger)]">{jobState.error_message}</p>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap gap-3 xl:w-72 xl:flex-col">
                      <button
                        type="button"
                        onClick={() => void handleIngest(document.id)}
                        disabled={busy}
                        className="button-primary"
                      >
                        {busy ? "Indexing..." : "Start indexing"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDelete(document.id)}
                        className="button-secondary"
                      >
                        Delete document
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.4rem] bg-white/76 px-4 py-4">
      <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--ink)]">{value}</p>
    </div>
  );
}
