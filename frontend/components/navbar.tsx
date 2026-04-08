"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";

interface NavbarProps {
    authenticated?: boolean;
}

const NAV_LINKS = [
    { href: "/collections", label: "Dashboard" },
];

export function Navbar({ authenticated = false }: NavbarProps) {
    const pathname = usePathname();
    const router = useRouter();
    const { session, logout } = useAuth();

    return (
        <nav className="sticky top-0 z-50 border-b border-(--line) bg-[rgba(242,235,223,0.85)] backdrop-blur-2xl">
            <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
                <div className="flex items-center gap-8">
                    <Link href={authenticated ? "/collections" : "/"} className="flex items-center gap-2.5">
                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent) text-white">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                <path d="M3 2h7l3 3v9H3V2z" fill="currentColor" opacity="0.9" />
                                <path d="M5 5h4M5 8h6M5 11h3" stroke="rgba(255,255,255,0.6)" strokeWidth="1.2" strokeLinecap="round" />
                            </svg>
                        </span>
                        <span className="text-xl font-bold tracking-tight text-[var(--ink)]">Folio</span>
                    </Link>

                    {authenticated ? (
                        <div className="hidden items-center gap-1 sm:flex">
                            {NAV_LINKS.map((link) => {
                                const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
                                return (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        className={`rounded-lg px-3 py-2 text-sm font-medium transition ${active
                                            ? "bg-[rgba(188,93,60,0.12)] text-[var(--accent-deep)]"
                                            : "text-[var(--muted)] hover:bg-white/60 hover:text-[var(--ink)]"
                                            }`}
                                    >
                                        {link.label}
                                    </Link>
                                );
                            })}
                        </div>
                    ) : null}
                </div>

                {authenticated && session ? (
                    <div className="flex items-center gap-4">
                        <span className="hidden text-sm text-[var(--muted)] sm:block">
                            {session.user.full_name}
                        </span>
                        <button
                            type="button"
                            onClick={async () => {
                                await logout();
                                router.replace("/");
                            }}
                            className="rounded-lg border border-[var(--line)] bg-white/70 px-3 py-1.5 text-sm font-medium text-[var(--muted)] transition hover:bg-white hover:text-[var(--ink)]"
                        >
                            Sign out
                        </button>
                    </div>
                ) : null}
            </div>
        </nav>
    );
}