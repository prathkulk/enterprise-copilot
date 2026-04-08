"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useEffectEvent, useState } from "react";
import { CollectionSwitcher } from "@/components/collection-switcher";
import { DashboardShell } from "@/components/dashboard-shell";
import { useAuth } from "@/components/auth-provider";
import { ApiError, fetchCollections, fetchDocuments, uploadDocument } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Collection, DocumentListItem, DocumentUploadResponse } from "@/lib/types";

export default function UploadPage() {
  const params = useParams<{ collectionId: string }>();
  const collectionId = Number(params.collectionId);
  const { session } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [lastUpload, setLastUpload] = useState<DocumentUploadResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCollection = collections.find((item) => item.id === collectionId) ?? null;
  const refreshEvent = useEffectEvent(() => { void refresh(); });

  async function refresh() {
    setLoading(true);
    try {
      const [c, d] = await Promise.all([fetchCollections(), fetchDocuments(collectionId)]);
      setCollections(c);
      setDocuments(d);
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.detail : "Couldn't load this collection right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session || Number.isNaN(collectionId)) return;
    refreshEvent();
  }, [collectionId, session]);

  async function submitUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) { setError("Pick a file first."); return; }
    setBusy(true);
    setError(null);
    try {
      const uploaded = await uploadDocument(collectionId, selectedFile);
      setLastUpload(uploaded);
      setSelectedFile(null);
      await refresh();
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.detail : "Upload failed. Try again?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      title="Upload"
      description="Add documents to this collection."
      collectionName={selectedCollection?.name}
      collectionId={collectionId}
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="space-y-5">
          <div className="panel rounded-[1.6rem] p-6">
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-xl font-semibold">Add a file</h3>
              <Link href={`/collections/${collectionId}/documents`} className="button-secondary !py-2 text-sm">
                Process documents
              </Link>
            </div>

            {collections.length > 1 ? (
              <div className="mt-5">
                <CollectionSwitcher
                  collections={collections}
                  selectedCollectionId={selectedCollection?.id ?? null}
                  routeBuilder={(id) => `/collections/${id}/upload`}
                />
              </div>
            ) : null}

            <form className="mt-5 space-y-4" onSubmit={submitUpload}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--muted)]">Choose a file</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="field file:mr-4 file:rounded-full file:border-0 file:bg-[rgba(188,93,60,0.12)] file:px-4 file:py-2 file:font-medium file:text-[var(--accent-deep)]"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                />
              </label>
              <p className="text-sm text-[var(--muted)]">
                PDF, Word (.docx), and plain text files accepted.
              </p>

              {error ? (
                <div className="rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                  {error}
                </div>
              ) : null}

              <button type="submit" disabled={busy} className="button-primary w-full">
                {busy ? "Uploading..." : "Upload"}
              </button>
            </form>

            {lastUpload ? (
              <div className="mt-5 rounded-xl border border-[rgba(29,107,76,0.18)] bg-[rgba(29,107,76,0.08)] p-4">
                <p className="text-sm font-semibold text-[var(--success)]">Uploaded: {lastUpload.filename}</p>
                <p className="mt-1 text-sm text-[var(--muted)]">Ready to be processed.</p>
              </div>
            ) : null}
          </div>
        </section>

        <section className="space-y-4">
          <div className="panel rounded-[1.6rem] p-6">
            <h3 className="text-xl font-semibold">Files in this collection</h3>
          </div>

          {loading ? (
            <div className="panel rounded-[1.6rem] p-6 text-[var(--muted)]">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="panel rounded-[1.6rem] p-8 text-center">
              <p className="text-[var(--muted)]">Nothing here yet. Upload your first file.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <article key={doc.id} className="panel rounded-[1.6rem] p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase text-[var(--muted)]">{doc.source_type.toUpperCase()}</p>
                    <h4 className="mt-1 text-lg font-semibold">{doc.filename}</h4>
                    <p className="mt-1 text-sm text-[var(--muted)]">Uploaded {formatDate(doc.uploaded_at)}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-white/72 px-3 py-1.5 text-xs font-semibold capitalize text-[var(--ink)]">
                    {doc.status}
                  </span>
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </DashboardShell>
  );
}