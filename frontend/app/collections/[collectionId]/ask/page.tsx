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
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't load the collections yet.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session || Number.isNaN(collectionId)) {
      return;
    }

    void refreshCollections();
  }, [collectionId, session]);

  async function submitQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const answer = await askCollection({
        question,
        collection_id: collectionId,
      });
      setResponse(answer);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't answer that yet.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      title="Ask a question"
      description="Ask in plain language, then keep the answer, the source cards, and the supporting text all in one view."
    >
      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <section className="space-y-6">
          <div className="panel rounded-[1.8rem] p-6">
            <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
              Step 4
            </p>
            <h3 className="mt-3 text-2xl font-semibold">
              {selectedCollection?.name ?? "Loading collection..."}
            </h3>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Ask about this collection the way you would ask a teammate. The answer should read naturally, and the evidence should stay easy to inspect.
            </p>

            <div className="mt-6">
              {collections.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                  <CollectionSwitcher
                    collections={collections}
                    selectedCollectionId={selectedCollection?.id ?? null}
                    routeBuilder={(nextCollectionId) => `/collections/${nextCollectionId}/ask`}
                  />
                  <button type="button" onClick={() => void refreshCollections()} className="button-secondary">
                    Refresh
                  </button>
                </div>
              ) : null}
            </div>

            {error ? (
              <div className="mt-5 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                {error}
              </div>
            ) : null}

            <form className="mt-6 space-y-4" onSubmit={submitQuestion}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                  Question
                </span>
                <textarea
                  required
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  className="field min-h-40 resize-y"
                  placeholder="What strengths and experience does this resume highlight?"
                />
              </label>
              <button type="submit" disabled={busy || loading} className="button-primary w-full">
                {busy ? "Writing answer..." : "Ask question"}
              </button>
            </form>
          </div>

          <div className="panel rounded-[1.8rem] p-6">
            <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent-cool)]">
              What to look for
            </p>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted)]">
              <li>The answer should sound human and direct, not like a debug statement.</li>
              <li>The source cards should point back to real files and real chunks.</li>
              <li>If the evidence is thin, the app should be honest about that without sounding evasive.</li>
            </ul>
          </div>
        </section>

        <section className="space-y-4">
          <div className="panel rounded-[1.8rem] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent-cool)]">
                  Answer
                </p>
                <h3 className="mt-3 text-2xl font-semibold">What the app found</h3>
              </div>
              {response ? <ConfidenceBadge confidence={response.confidence} /> : null}
            </div>

            {loading ? (
              <p className="mt-6 text-[var(--muted)]">Loading collections...</p>
            ) : response ? (
              <>
                <article className="mt-6 rounded-[1.6rem] bg-white/78 p-5">
                  <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    Final answer
                  </p>
                  <p className="mt-4 text-lg leading-8">{response.answer}</p>
                  {response.missing_information.length > 0 ? (
                    <div className="mt-5 rounded-[1.4rem] bg-[rgba(138,97,25,0.08)] px-4 py-4">
                      <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--warning)]">
                        What the documents still don&apos;t cover
                      </p>
                      <ul className="mt-3 space-y-2 text-sm text-[var(--muted)]">
                        {response.missing_information.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </article>

                <div className="grid gap-4 md:grid-cols-3">
                  <MetricCard label="Total time" value={`${formatNumber(response.latency_ms.total_ms)} ms`} />
                  <MetricCard label="Prompt version" value={response.prompt_version} />
                  <MetricCard label="Model" value={response.providers.llm_model} />
                </div>
              </>
            ) : (
              <div className="mt-6 rounded-[1.6rem] border border-dashed border-[var(--line)] px-5 py-10 text-center">
                <h4 className="text-xl font-semibold">No answer yet</h4>
                <p className="mt-3 text-[var(--muted)]">
                  Ask something real and this area will fill with the answer, the sources, and the supporting text.
                </p>
              </div>
            )}
          </div>

          {response?.citations.length ? (
            <div className="panel rounded-[1.8rem] p-6">
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
                Sources
              </p>
              <div className="mt-4 grid gap-4">
                {response.citations.map((citation) => {
                  const supportingChunk = response.retrieved_chunks.find(
                    (chunk) => chunk.citation.chunk_id === citation.chunk_id,
                  );

                  return (
                    <article key={citation.chunk_id} className="rounded-[1.5rem] bg-white/78 p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--accent)]">
                            {citation.marker} {citation.label}
                          </p>
                          <h4 className="mt-2 text-lg font-semibold">{citation.filename}</h4>
                        </div>
                        <div className="rounded-full bg-[rgba(28,85,107,0.1)] px-3 py-1 text-sm font-medium text-[var(--accent-cool)]">
                          score {formatNumber(citation.score)}
                        </div>
                      </div>
                      <p className="mt-3 text-sm text-[var(--muted)]">
                        Chunk {citation.chunk_index}
                        {citation.page_reference ? ` · page ${citation.page_reference}` : ""}
                        {citation.start_char !== null && citation.end_char !== null
                          ? ` · chars ${citation.start_char}-${citation.end_char}`
                          : ""}
                      </p>
                      {supportingChunk ? (
                        <p className="mt-4 rounded-[1.3rem] bg-[rgba(21,37,52,0.04)] px-4 py-4 text-sm leading-7 text-[var(--ink)]">
                          {supportingChunk.text}
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </div>
          ) : null}

          {response?.retrieved_chunks.length ? (
            <div className="panel rounded-[1.8rem] p-6">
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent-cool)]">
                Supporting text
              </p>
              <div className="mt-4 grid gap-4">
                {response.retrieved_chunks.map((chunk) => (
                  <article key={chunk.citation.chunk_id} className="rounded-[1.5rem] bg-white/78 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h4 className="text-lg font-semibold">{chunk.citation.filename}</h4>
                      <div className="rounded-full bg-[rgba(188,93,60,0.1)] px-3 py-1 text-sm font-medium text-[var(--accent-deep)]">
                        relevance {formatNumber(chunk.score)}
                      </div>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{chunk.text}</p>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </DashboardShell>
  );
}

function ConfidenceBadge({
  confidence,
}: {
  confidence: "grounded" | "partial" | "insufficient_evidence";
}) {
  const styles = {
    grounded: "bg-[rgba(29,107,76,0.12)] text-[var(--success)]",
    partial: "bg-[rgba(138,97,25,0.12)] text-[var(--warning)]",
    insufficient_evidence: "bg-[rgba(159,47,47,0.12)] text-[var(--danger)]",
  };

  return (
    <span className={`rounded-full px-4 py-2 text-sm font-semibold capitalize ${styles[confidence]}`}>
      {confidence.replaceAll("_", " ")}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.4rem] bg-white/78 px-4 py-4">
      <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--ink)]">{value}</p>
    </div>
  );
}
