"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { Navbar } from "@/components/navbar";
import { ApiError, loginUser, registerUser } from "@/lib/api";

type AuthMode = "register" | "login";

export default function HomePage() {
  const router = useRouter();
  const { ready, session, saveAuth } = useAuth();
  const [mode, setMode] = useState<AuthMode>("register");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registerForm, setRegisterForm] = useState({
    tenant_name: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  });

  useEffect(() => {
    if (ready && session) {
      router.replace("/collections");
    }
  }, [ready, router, session]);

  async function submitRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const response = await registerUser(registerForm);
      saveAuth(response);
      router.replace("/collections");
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.detail
          : "Something went wrong. Give it another try?",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const response = await loginUser(loginForm);
      saveAuth(response);
      router.replace("/collections");
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError ? caughtError.detail : "Couldn't sign you in. Try again?",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!ready || session) {
    return (
      <>
        <Navbar />
        <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-6 py-12">
          <div className="panel w-full max-w-lg rounded-[2rem] p-8 text-center">
            <h1 className="text-2xl font-semibold">One moment...</h1>
          </div>
        </main>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="min-h-[calc(100vh-4rem)] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto grid min-h-[calc(100vh-7rem)] max-w-7xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="panel relative overflow-hidden rounded-[2.2rem] p-8 sm:p-10 lg:p-14">
            <div className="absolute inset-x-0 top-0 h-40 bg-[radial-gradient(circle_at_top,rgba(188,93,60,0.26),transparent_62%)]" />
            <div className="relative">
              <h1 className="mt-6 max-w-3xl text-5xl font-semibold leading-[1.04] tracking-tight sm:text-6xl">
                Get answers from
                <br />
                your own documents.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-[var(--muted)]">
                Upload a file, let Folio read through it, then ask questions in plain language.
                Every answer comes with the exact source text so you can verify it yourself.
              </p>

              <div className="mt-10 grid gap-4 sm:grid-cols-3">
                {[
                  {
                    label: "Upload anything",
                    text: "PDFs, Word docs, or plain text. Drop in a resume, a handbook, meeting notes — whatever you need answers from.",
                  },
                  {
                    label: "Ask naturally",
                    text: "No special syntax. Just ask like you'd ask a colleague who read the whole thing.",
                  },
                  {
                    label: "See the proof",
                    text: "Every answer links back to the exact passage it came from, so you never have to take it on faith.",
                  },
                ].map((item) => (
                  <div key={item.label} className="panel-strong rounded-[1.6rem] p-5">
                    <p className="ui-mono text-xs uppercase tracking-[0.2em] text-[var(--accent)]">
                      {item.label}
                    </p>
                    <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{item.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="panel rounded-[2.2rem] p-6 sm:p-8">
            <div className="flex items-center justify-between">
              <h2 className="text-3xl font-semibold">Get started</h2>
              <div className="rounded-full bg-white/70 p-1">
                <button
                  type="button"
                  onClick={() => setMode("register")}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${mode === "register"
                      ? "bg-[var(--accent)] text-white"
                      : "text-[var(--muted)]"
                    }`}
                >
                  New here
                </button>
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${mode === "login"
                      ? "bg-[var(--accent)] text-white"
                      : "text-[var(--muted)]"
                    }`}
                >
                  Sign in
                </button>
              </div>
            </div>

            <p className="mt-5 text-sm leading-6 text-[var(--muted)]">
              {mode === "register"
                ? "Create a workspace and you're ready to go."
                : "Welcome back. Pick up right where you left off."}
            </p>

            {error ? (
              <div className="mt-5 rounded-2xl border border-[rgba(159,47,47,0.18)] bg-[rgba(159,47,47,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
                {error}
              </div>
            ) : null}

            {mode === "register" ? (
              <form className="mt-6 space-y-4" onSubmit={submitRegister}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                    Workspace name
                  </span>
                  <input
                    required
                    value={registerForm.tenant_name}
                    onChange={(event) =>
                      setRegisterForm((current) => ({
                        ...current,
                        tenant_name: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="e.g. Marketing Team"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                    Your name
                  </span>
                  <input
                    required
                    value={registerForm.full_name}
                    onChange={(event) =>
                      setRegisterForm((current) => ({
                        ...current,
                        full_name: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="Jane Smith"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">Email</span>
                  <input
                    required
                    type="email"
                    value={registerForm.email}
                    onChange={(event) =>
                      setRegisterForm((current) => ({
                        ...current,
                        email: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="you@company.com"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                    Password
                  </span>
                  <input
                    required
                    type="password"
                    minLength={8}
                    value={registerForm.password}
                    onChange={(event) =>
                      setRegisterForm((current) => ({
                        ...current,
                        password: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="At least 8 characters"
                  />
                </label>
                <button type="submit" className="button-primary w-full" disabled={busy}>
                  {busy ? "Setting things up..." : "Create workspace"}
                </button>
              </form>
            ) : (
              <form className="mt-6 space-y-4" onSubmit={submitLogin}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">Email</span>
                  <input
                    required
                    type="email"
                    value={loginForm.email}
                    onChange={(event) =>
                      setLoginForm((current) => ({
                        ...current,
                        email: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="you@company.com"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-[var(--muted)]">
                    Password
                  </span>
                  <input
                    required
                    type="password"
                    minLength={8}
                    value={loginForm.password}
                    onChange={(event) =>
                      setLoginForm((current) => ({
                        ...current,
                        password: event.target.value,
                      }))
                    }
                    className="field"
                    placeholder="Your password"
                  />
                </label>
                <button type="submit" className="button-primary w-full" disabled={busy}>
                  {busy ? "Signing in..." : "Sign in"}
                </button>
              </form>
            )}
          </section>
        </div>
      </main>
    </>
  );
}