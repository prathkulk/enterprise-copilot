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
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't load this collection yet.",
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

  async function submitUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setError("Choose a PDF, DOCX, or TXT file to upload.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const uploaded = await uploadDocument(collectionId, selectedFile);
      setLastUpload(uploaded);
      setSelectedFile(null);
      await refreshPageData();
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't upload that file yet.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      title="Upload"
      description="Bring in a file you actually care about. The rest of the story gets much easier to follow when the content is real."
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="panel rounded-[1.8rem] p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
                Step 2
              </p>
              <h3 className="mt-3 text-2xl font-semibold">Add a document to this collection</h3>
            </div>
            <Link
              href={`/collections/${collectionId}/documents`}
              className="button-secondary whitespace-nowrap"
            >
              Go to indexing
            </Link>
          </div>

          <div className="mt-6">
            {collections.length > 0 ? (
              <CollectionSwitcher
                collections={collections}
                selectedCollectionId={selectedCollection?.id ?? null}
                routeBuilder={(nextCollectionId) => `/collections/${nextCollectionId}/upload`}
              />
            ) : null}
          </div>

          <form className="mt-6 space-y-4" onSubmit={submitUpload}>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--muted)]">File</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="field file:mr-4 file:rounded-full file:border-0 file:bg-[rgba(188,93,60,0.12)] file:px-4 file:py-2 file:font-medium file:text-[var(--accent-deep)]"
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null;
                  setSelectedFile(nextFile);
                }}
              />
            </label>

            <div className="rounded-[1.4rem] bg-white/72 px-4 py-4 text-sm text-[var(--muted)]">
              Accepted formats: <span className="font-semibold text-[var(--ink)]">PDF, DOCX, TXT</span>.
              This file will be added to{" "}
              <span className="font-semibold text-[var(--ink)]">
                {selectedCollection?.name ?? "the selected collection"}
              </span>
              .
            </div>

            {error ? (
              <div className="rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                {error}
              </div>
            ) : null}

            <button type="submit" disabled={busy} className="button-primary w-full">
              {busy ? "Uploading..." : "Upload file"}
            </button>
          </form>

          {lastUpload ? (
            <div className="mt-6 rounded-[1.6rem] border border-[rgba(29,107,76,0.18)] bg-[rgba(29,107,76,0.08)] p-5">
              <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--success)]">
                Just uploaded
              </p>
              <h4 className="mt-3 text-lg font-semibold">{lastUpload.filename}</h4>
              <p className="mt-2 text-sm text-[var(--muted)]">
                It&apos;s safely stored and ready for indexing when you are.
              </p>
            </div>
          ) : null}
        </section>

        <section className="space-y-4">
          <div className="panel rounded-[1.8rem] p-6">
            <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent-cool)]">
              Already here
            </p>
            <h3 className="mt-3 text-2xl font-semibold">
              {selectedCollection?.name ?? "Collection documents"}
            </h3>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Recent uploads appear here right away. If something looks good, head to the next page and turn it into searchable context.
            </p>
          </div>

          {loading ? (
            <div className="panel rounded-[1.8rem] p-6 text-[var(--muted)]">
              Loading this collection...
            </div>
          ) : documents.length === 0 ? (
            <div className="panel rounded-[1.8rem] p-8 text-center">
              <h4 className="text-xl font-semibold">No files here yet</h4>
              <p className="mt-3 text-[var(--muted)]">
                Upload one document and the rest of the flow will start to feel real.
              </p>
            </div>
          ) : (
            documents.map((document) => (
              <article key={document.id} className="panel rounded-[1.8rem] p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
                      {document.source_type} document
                    </p>
                    <h4 className="mt-3 text-xl font-semibold">{document.filename}</h4>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      Uploaded {formatDate(document.uploaded_at)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-white/72 px-4 py-3 text-sm">
                    <span className="font-semibold text-[var(--ink)]">{document.status}</span>
                  </div>
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
