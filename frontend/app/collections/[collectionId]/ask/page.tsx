"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { CollectionSwitcher } from "@/components/collection-switcher";
import { DashboardShell } from "@/components/dashboard-shell";
import { useAuth } from "@/components/auth-provider";
import { ApiError, askCollection, fetchCollections } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { AskResponse, Collection } from "@/lib/types";

export default function AskPage() {
  const params = useParams<{ collectionId: string }>();
  const collectionId = Number(params.collectionId);
  const { session } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCollection = collections.find((item) => item.id === collectionId) ?? null;

  async function refreshCollections() {
    setLoading(true);
    try {
      const nextCollections = await fetchCollections();
      setCollections(nextCollections);
      setError(null);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "Couldn't load collections right now.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session || Number.isNaN(collectionId)) return;
    void refreshCollections();
  }, [collectionId, session]);

  async function submitQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const answer = await askCollection({ question, collection_id: collectionId });
      setResponse(answer);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "Couldn't get an answer right now. Try again?",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      title="Ask"
      description="Ask about your documents in plain language."
      collectionName={selectedCollection?.name}
      collectionId={collectionId}
    >
      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <section className="space-y-6">
          <div className="panel rounded-[1.6rem] p-6">
            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              The more specific your question, the better the answer.
            </p>

            {collections.length > 1 ? (
              <div className="mt-5">
                <CollectionSwitcher
                  collections={collections}
                  selectedCollectionId={selectedCollection?.id ?? null}
                  routeBuilder={(id) => `/collections/${id}/ask`}
                />
              </div>
            ) : null}

            {error ? (
              <div className="mt-5 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                {error}
              </div>
            ) : null}

            <form className="mt-5 space-y-4" onSubmit={submitQuestion}>
              <textarea
                required
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="field min-h-36 resize-y"
                placeholder="e.g. What are the key qualifications listed in this resume?"
              />
              <button type="submit" disabled={busy || loading} className="button-primary w-full">
                {busy ? "Thinking..." : "Ask"}
              </button>
            </form>
          </div>

          <div className="panel rounded-[1.6rem] p-5">
            <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent-cool)]">Tips</p>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--muted)]">
              <li>Be specific — &quot;What Python experience does this person have?&quot; beats &quot;Tell me about this resume.&quot;</li>
              <li>If there isn&apos;t enough info, Folio will say so rather than guess.</li>
              <li>Check the sources below each answer to verify.</li>
            </ul>
          </div>
        </section>

        <section className="space-y-4">
          <div className="panel rounded-[1.6rem] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-2xl font-semibold">Answer</h3>
              {response ? <ConfidenceBadge confidence={response.confidence} /> : null}
            </div>

            {loading ? (
              <p className="mt-6 text-[var(--muted)]">Loading...</p>
            ) : response ? (
              <>
                <article className="mt-6 rounded-[1.4rem] bg-white/78 p-5">
                  <p className="text-lg leading-8">{response.answer}</p>
                  {response.missing_information.length > 0 ? (
                    <div className="mt-5 rounded-xl bg-[rgba(138,97,25,0.08)] px-4 py-3">
                      <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--warning)]">
                        Not fully covered in your documents
                      </p>
                      <ul className="mt-2 space-y-1 text-sm text-[var(--muted)]">
                        {response.missing_information.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </article>
                <p className="mt-3 text-sm text-[var(--muted)]">
                  Answered in {formatNumber(response.latency_ms.total_ms / 1000)}s
                  {response.citations.length > 0
                    ? ` · ${response.citations.length} source${response.citations.length === 1 ? "" : "s"}`
                    : ""}
                </p>
              </>
            ) : (
              <div className="mt-6 rounded-[1.4rem] border border-dashed border-[var(--line)] px-5 py-10 text-center">
                <p className="text-[var(--muted)]">Your answer will appear here.</p>
              </div>
            )}
          </div>

          {response?.citations.length ? (
            <div className="panel rounded-[1.6rem] p-6">
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">Sources</p>
              <div className="mt-4 grid gap-3">
                {response.citations.map((citation) => {
                  const chunk = response.retrieved_chunks.find(
                    (c) => c.citation.chunk_id === citation.chunk_id,
                  );
                  return (
                    <article key={citation.chunk_id} className="rounded-[1.3rem] bg-white/78 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <h4 className="font-semibold">{citation.filename}</h4>
                          <p className="text-xs text-[var(--muted)]">
                            {citation.page_reference
                              ? `Page ${citation.page_reference}`
                              : `Section ${citation.chunk_index + 1}`}
                          </p>
                        </div>
                        <span className="rounded-full bg-[rgba(28,85,107,0.1)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-cool)]">
                          {Math.round(citation.score * 100)}% match
                        </span>
                      </div>
                      {chunk ? (
                        <p className="mt-3 rounded-xl bg-[rgba(21,37,52,0.04)] px-3 py-3 text-sm leading-7 text-[var(--ink)]">
                          {chunk.text}
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </DashboardShell>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const config: Record<string, { style: string; label: string }> = {
    grounded: { style: "bg-[rgba(29,107,76,0.12)] text-[var(--success)]", label: "Fully supported" },
    partial: { style: "bg-[rgba(138,97,25,0.12)] text-[var(--warning)]", label: "Partially supported" },
    insufficient_evidence: { style: "bg-[rgba(159,47,47,0.12)] text-[var(--danger)]", label: "Not enough info" },
  };
  const { style, label } = config[confidence] ?? config.partial;
  return <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${style}`}>{label}</span>;
}