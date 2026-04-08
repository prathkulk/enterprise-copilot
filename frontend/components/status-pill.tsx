interface StatusPillProps {
  status: string;
}

const STATUS_STYLES: Record<string, string> = {
  uploaded: "bg-[rgba(28,85,107,0.10)] text-[var(--accent-cool)]",
  pending: "bg-[rgba(138,97,25,0.12)] text-[var(--warning)]",
  processing: "bg-[rgba(188,93,60,0.12)] text-[var(--accent-deep)]",
  indexed: "bg-[rgba(29,107,76,0.12)] text-[var(--success)]",
  failed: "bg-[rgba(159,47,47,0.12)] text-[var(--danger)]",
};

export function StatusPill({ status }: StatusPillProps) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
        STATUS_STYLES[status] ?? "bg-[rgba(21,37,52,0.08)] text-[var(--muted)]"
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}
