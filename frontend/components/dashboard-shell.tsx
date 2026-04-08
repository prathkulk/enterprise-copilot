"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/auth-provider";

interface DashboardShellProps {
  title: string;
  description: string;
  children: React.ReactNode;
}

export function DashboardShell({
  title,
  description,
  children,
}: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { ready, session, logout } = useAuth();

  useEffect(() => {
    if (ready && !session) {
      router.replace("/");
    }
  }, [ready, router, session]);

  if (!ready || !session) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="panel w-full max-w-lg rounded-[2rem] p-8 text-center">
          <p className="ui-mono text-sm uppercase tracking-[0.28em] text-[var(--accent-cool)]">
            Enterprise Copilot
          </p>
          <h1 className="mt-4 text-3xl font-semibold">Opening your workspace...</h1>
          <p className="mt-3 text-[var(--muted)]">
            We&apos;re checking your session and bringing you back to your documents.
          </p>
        </div>
      </main>
    );
  }

  const navItems = [{ href: "/collections", label: "Collections" }];

  return (
    <main className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-7xl flex-col gap-6 lg:flex-row">
        <aside className="panel rounded-[2rem] p-5 lg:w-80 lg:p-6">
          <div className="rounded-[1.6rem] bg-[rgba(28,85,107,0.95)] px-5 py-6 text-white shadow-[0_24px_50px_rgba(28,85,107,0.22)]">
            <p className="ui-mono text-xs uppercase tracking-[0.3em] text-white/70">
              Your workspace
            </p>
            <h1 className="mt-3 text-3xl font-semibold leading-tight">
              Ask real questions.
              <br />
              Keep the receipts.
            </h1>
            <p className="mt-4 text-sm leading-6 text-white/78">
              Upload something meaningful, let it index in the background, and read answers with
              the source text close by.
            </p>
          </div>

          <div className="mt-5 space-y-2">
            {navItems.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between rounded-2xl px-4 py-3 transition ${
                    active
                      ? "bg-[rgba(188,93,60,0.12)] text-[var(--accent-deep)]"
                      : "text-[var(--muted)] hover:bg-white/70 hover:text-[var(--ink)]"
                  }`}
                >
                  <span className="font-medium">{item.label}</span>
                  <span className="ui-mono text-xs uppercase tracking-[0.18em]">
                    Open
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="mt-6 rounded-[1.6rem] border border-white/70 bg-white/82 p-4">
            <p className="ui-mono text-xs uppercase tracking-[0.22em] text-[var(--accent-cool)]">
              Signed in
            </p>
            <div className="mt-3">
              <p className="text-lg font-semibold">{session.user.full_name}</p>
              <p className="text-sm text-[var(--muted)]">{session.user.email}</p>
            </div>
            <div className="mt-4 rounded-2xl bg-[rgba(21,37,52,0.04)] px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Workspace</p>
              <p className="mt-1 text-sm font-medium">{session.tenant.name}</p>
            </div>
            <button
              type="button"
              onClick={async () => {
                await logout();
                router.replace("/");
              }}
              className="button-secondary mt-4 w-full"
            >
              Sign out
            </button>
          </div>
        </aside>

        <section className="flex-1 rounded-[2rem] border border-white/60 bg-[rgba(255,252,247,0.78)] p-5 shadow-[0_20px_60px_rgba(18,25,33,0.08)] backdrop-blur-xl sm:p-6 lg:p-8">
          <header className="mb-8 flex flex-col gap-4 border-b border-[var(--line)] pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="ui-mono text-xs uppercase tracking-[0.24em] text-[var(--accent)]">
                Today&apos;s flow
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">{title}</h2>
              <p className="mt-3 max-w-3xl text-[var(--muted)]">{description}</p>
            </div>
            <div className="rounded-2xl bg-white/70 px-4 py-3 text-sm text-[var(--muted)]">
              <span className="font-medium text-[var(--ink)]">Security:</span> the browser never
              stores your bearer token in client storage
            </div>
          </header>

          {children}
        </section>
      </div>
    </main>
  );
}
