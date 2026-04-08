"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Navbar } from "@/components/navbar";
import { ApiError, createCollection, fetchCollections } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Collection } from "@/lib/types";

export default function CollectionsPage() {
  const { ready, session } = useAuth();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const router = useRouter();

  async function handleRefresh() {
    setLoading(true);
    try {
      const response = await fetchCollections();
      setCollections(response);
      setError(null);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.detail
          : "Couldn't load your collections right now.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!session) return;
    void handleRefresh();
  }, [session]);

  useEffect(() => {
    if (ready && !session) {
      router.replace("/");
    }
  }, [ready, session, router]);

  async function submitCollection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const created = await createCollection(form);
      setCollections((current) => [created, ...current]);
      setForm({ name: "", description: "" });
      setShowForm(false);
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.detail
          : "Couldn't create that collection. Try again?",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!ready || !session) {
    return (
      <>
        <Navbar />
        <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
          <div className="panel rounded-[2rem] p-8 text-center">
            <h1 className="text-2xl font-semibold">One moment...</h1>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Navbar authenticated />
      <main className="min-h-[calc(100vh-4rem)] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col gap-6 lg:flex-row">
            {/* ─── Sidebar ─── */}
            <aside className="shrink-0 space-y-5 lg:w-72">
              {/* User card */}
              <div className="panel rounded-[1.6rem] p-5">
                <p className="text-lg font-semibold">{session.user.full_name}</p>
                <p className="mt-1 text-sm text-[var(--muted)]">{session.user.email}</p>
                <div className="mt-4 rounded-xl bg-[rgba(21,37,52,0.04)] px-3 py-2.5">
                  <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    Workspace
                  </p>
                  <p className="mt-0.5 text-sm font-medium">{session.tenant.name}</p>
                </div>
              </div>

              {/* Quick stats */}
              <div className="panel rounded-[1.6rem] p-5">
                <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent-cool)]">
                  Overview
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-white/70 px-3 py-3 text-center">
                    <p className="text-2xl font-bold text-[var(--ink)]">{collections.length}</p>
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      {collections.length === 1 ? "Collection" : "Collections"}
                    </p>
                  </div>
                  <div className="rounded-xl bg-white/70 px-3 py-3 text-center">
                    <p className="text-2xl font-bold text-[var(--ink)]">
                      {collections.length > 0
                        ? collections.filter(
                          (c) =>
                            new Date(c.updated_at).getTime() >
                            Date.now() - 7 * 24 * 60 * 60 * 1000,
                        ).length
                        : 0}
                    </p>
                    <p className="mt-1 text-xs text-[var(--muted)]">Active this week</p>
                  </div>
                </div>
              </div>

              {/* New collection */}
              <div className="panel rounded-[1.6rem] p-5">
                {showForm ? (
                  <>
                    <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent)]">
                      New collection
                    </p>
                    <form className="mt-4 space-y-3" onSubmit={submitCollection}>
                      <input
                        required
                        value={form.name}
                        onChange={(e) =>
                          setForm((f) => ({ ...f, name: e.target.value }))
                        }
                        className="field !py-2.5 text-sm"
                        placeholder="Collection name"
                      />
                      <textarea
                        value={form.description}
                        onChange={(e) =>
                          setForm((f) => ({ ...f, description: e.target.value }))
                        }
                        className="field min-h-20 resize-y !py-2.5 text-sm"
                        placeholder="Description (optional)"
                      />
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={busy}
                          className="button-primary flex-1 !py-2 text-sm"
                        >
                          {busy ? "Creating..." : "Create"}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowForm(false);
                            setForm({ name: "", description: "" });
                          }}
                          className="button-secondary !py-2 text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowForm(true)}
                    className="button-primary w-full"
                  >
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 16 16"
                      fill="none"
                      className="shrink-0"
                    >
                      <path
                        d="M8 3v10M3 8h10"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                    New collection
                  </button>
                )}
              </div>

              {/* Tips */}
              <div className="panel rounded-[1.6rem] p-5">
                <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent-cool)]">
                  How it works
                </p>
                <ol className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted)]">
                  <li className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[rgba(188,93,60,0.12)] text-xs font-bold text-[var(--accent)]">
                      1
                    </span>
                    Create a collection
                  </li>
                  <li className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[rgba(188,93,60,0.12)] text-xs font-bold text-[var(--accent)]">
                      2
                    </span>
                    Upload your documents
                  </li>
                  <li className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[rgba(188,93,60,0.12)] text-xs font-bold text-[var(--accent)]">
                      3
                    </span>
                    Process them to make searchable
                  </li>
                  <li className="flex gap-3">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[rgba(188,93,60,0.12)] text-xs font-bold text-[var(--accent)]">
                      4
                    </span>
                    Ask questions, get sourced answers
                  </li>
                </ol>
              </div>
            </aside>

            {/* ─── Main grid ─── */}
            <section className="flex-1">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-semibold tracking-tight">Your collections</h1>
                  <p className="mt-1 text-[var(--muted)]">
                    Everything you've organized, in one place.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleRefresh()}
                  className="button-secondary !py-2 text-sm"
                >
                  Refresh
                </button>
              </div>

              {error ? (
                <div className="mb-6 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                  {error}
                </div>
              ) : null}

              {loading ? (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="panel animate-pulse rounded-[1.6rem] p-6"
                    >
                      <div className="h-5 w-2/3 rounded-lg bg-[rgba(21,37,52,0.08)]" />
                      <div className="mt-3 h-4 w-full rounded-lg bg-[rgba(21,37,52,0.05)]" />
                      <div className="mt-2 h-4 w-1/2 rounded-lg bg-[rgba(21,37,52,0.05)]" />
                    </div>
                  ))}
                </div>
              ) : collections.length === 0 ? (
                <div className="panel rounded-[1.8rem] p-10 text-center">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[rgba(188,93,60,0.1)]">
                    <svg
                      width="28"
                      height="28"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="text-[var(--accent)]"
                    >
                      <path
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <h3 className="mt-5 text-xl font-semibold">No collections yet</h3>
                  <p className="mt-2 text-[var(--muted)]">
                    Create your first collection to start uploading and searching documents.
                  </p>
                  <button
                    type="button"
                    onClick={() => setShowForm(true)}
                    className="button-primary mt-6"
                  >
                    Create your first collection
                  </button>
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {collections.map((collection) => (
                    <article
                      key={collection.id}
                      className="panel group relative rounded-[1.6rem] p-6 transition hover:shadow-[0_28px_70px_rgba(33,40,48,0.16)]"
                    >
                      <div className="mb-4 flex items-start justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[rgba(28,85,107,0.1)]">
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            className="text-[var(--accent-cool)]"
                          >
                            <path
                              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </div>
                        <span className="text-xs text-[var(--muted)]">
                          {formatDate(collection.updated_at)}
                        </span>
                      </div>

                      <h3 className="text-xl font-semibold leading-tight">
                        {collection.name}
                      </h3>
                      <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--muted)]">
                        {collection.description || "No description."}
                      </p>

                      <div className="mt-5 flex flex-wrap gap-2">
                        <Link
                          href={`/collections/${collection.id}/upload`}
                          className="rounded-full bg-[rgba(188,93,60,0.1)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-deep)] transition hover:bg-[rgba(188,93,60,0.18)]"
                        >
                          Upload
                        </Link>
                        <Link
                          href={`/collections/${collection.id}/documents`}
                          className="rounded-full bg-[rgba(28,85,107,0.08)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-cool)] transition hover:bg-[rgba(28,85,107,0.15)]"
                        >
                          Documents
                        </Link>
                        <Link
                          href={`/collections/${collection.id}/ask`}
                          className="rounded-full bg-[rgba(29,107,76,0.08)] px-3 py-1.5 text-xs font-semibold text-[var(--success)] transition hover:bg-[rgba(29,107,76,0.15)]"
                        >
                          Ask
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      </main>
    </>
  );
}