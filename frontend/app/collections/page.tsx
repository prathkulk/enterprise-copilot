"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { DashboardShell } from "@/components/dashboard-shell";
import { useAuth } from "@/components/auth-provider";
import { ApiError, createCollection, fetchCollections } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Collection } from "@/lib/types";

export default function CollectionsPage() {
  const { session } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
  });

  async function handleRefresh() {
    setLoading(true);
    try {
      const response = await fetchCollections();
      setCollections(response);
      setError(null);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't load your collections.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session) {
      return;
    }

    void handleRefresh();
  }, [session]);

  async function submitCollection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const created = await createCollection(form);
      setCollections((current) => [created, ...current]);
      setForm({ name: "", description: "" });
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "We couldn't create that collection yet.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      title="Collections"
      description="Start with a collection that makes sense to a human being. Once it exists, the rest of the workflow feels natural."
    >
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="panel rounded-[1.8rem] p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
                Step 1
              </p>
              <h3 className="mt-3 text-2xl font-semibold">Create a place for your documents</h3>
            </div>
            <button type="button" onClick={() => void handleRefresh()} className="button-secondary">
              Refresh
            </button>
          </div>

          <p className="mt-4 text-sm leading-6 text-[var(--muted)]">
            A collection can be as broad as &quot;Team Handbook&quot; or as specific as &quot;Resume Review&quot;.
            Keep it intuitive. If the name feels obvious to you, it will feel obvious in the demo too.
          </p>

          {error ? (
            <div className="mt-5 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
              {error}
            </div>
          ) : null}

          <form className="mt-6 space-y-4" onSubmit={submitCollection}>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--muted)]">Name</span>
              <input
                required
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                className="field"
                placeholder="Resume Review"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                Description
              </span>
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                className="field min-h-32 resize-y"
                placeholder="A collection for resumes, portfolio notes, or anything I want to ask thoughtful questions about."
              />
            </label>
            <button type="submit" disabled={busy} className="button-primary w-full">
              {busy ? "Creating..." : "Create collection"}
            </button>
          </form>
        </section>

        <section className="space-y-4">
          <div className="panel rounded-[1.8rem] p-6">
            <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent-cool)]">
              Your collections
            </p>
            <div className="mt-4 flex items-end justify-between gap-4">
              <div>
                <h3 className="text-2xl font-semibold">Pick up where you left off</h3>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  Open any collection to add a file, watch it index, or ask a grounded question with sources.
                </p>
              </div>
              <div className="rounded-2xl bg-white/75 px-4 py-3 text-right">
                <p className="ui-mono text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                  Count
                </p>
                <p className="mt-1 text-2xl font-semibold">{collections.length}</p>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="panel rounded-[1.8rem] p-6 text-[var(--muted)]">
              Gathering your collections...
            </div>
          ) : collections.length === 0 ? (
            <div className="panel rounded-[1.8rem] p-8 text-center">
              <h4 className="text-xl font-semibold">Nothing here yet</h4>
              <p className="mt-3 text-[var(--muted)]">
                Create your first collection on the left and the rest of the experience opens up.
              </p>
            </div>
          ) : (
            collections.map((collection) => (
              <article key={collection.id} className="panel rounded-[1.8rem] p-6">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="ui-mono text-xs uppercase tracking-[0.22em] text-[var(--accent)]">
                      Collection {collection.id}
                    </p>
                    <h4 className="mt-3 text-2xl font-semibold">{collection.name}</h4>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
                      {collection.description || "No description yet, which is perfectly fine for a quick demo."}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-white/78 px-4 py-3 text-sm text-[var(--muted)]">
                    Updated {formatDate(collection.updated_at)}
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Link href={`/collections/${collection.id}/upload`} className="button-primary">
                    Add a document
                  </Link>
                  <Link href={`/collections/${collection.id}/documents`} className="button-secondary">
                    See documents
                  </Link>
                  <Link href={`/collections/${collection.id}/ask`} className="button-secondary">
                    Ask a question
                  </Link>
                </div>
              </article>
            ))
          )}
        </section>
      </div>
    </DashboardShell>
  );
}
