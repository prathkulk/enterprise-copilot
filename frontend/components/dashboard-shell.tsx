"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/components/auth-provider";
import { Navbar } from "@/components/navbar";

interface DashboardShellProps {
  title: string;
  description: string;
  collectionName?: string;
  collectionId?: number;
  children: React.ReactNode;
}

export function DashboardShell({
  title,
  description,
  collectionName,
  collectionId,
  children,
}: DashboardShellProps) {
  const router = useRouter();
  const { ready, session } = useAuth();

  useEffect(() => {
    if (ready && !session) {
      router.replace("/");
    }
  }, [ready, router, session]);

  if (!ready || !session) {
    return (
      <>
        <Navbar />
        <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-12">
          <div className="panel w-full max-w-lg rounded-[2rem] p-8 text-center">
            <h1 className="text-2xl font-semibold">One moment...</h1>
            <p className="mt-3 text-[var(--muted)]">Checking your session.</p>
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
          <header className="mb-8">
            {collectionName && collectionId ? (
              <div className="mb-3 flex items-center gap-2 text-sm text-[var(--muted)]">
                <Link href="/collections" className="transition hover:text-[var(--ink)]">
                  Dashboard
                </Link>
                <span className="text-[var(--line)]">/</span>
                <Link
                  href={`/collections/${collectionId}/documents`}
                  className="transition hover:text-[var(--ink)]"
                >
                  {collectionName}
                </Link>
                <span className="text-[var(--line)]">/</span>
                <span className="font-medium text-[var(--ink)]">{title}</span>
              </div>
            ) : null}
            <h2 className="text-3xl font-semibold tracking-tight">{title}</h2>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">{description}</p>
          </header>

          {children}
        </div>
      </main>
    </>
  );
}