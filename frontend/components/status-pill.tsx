interface StatusPillProps {
  status: string;
}

const STATUS_CONFIG: Record<string, { style: string; label: string }> = {
  uploaded: { style: "bg-[rgba(28,85,107,0.10)] text-[var(--accent-cool)]", label: "Uploaded" },
  pending: { style: "bg-[rgba(138,97,25,0.12)] text-[var(--warning)]", label: "Waiting" },
  processing: { style: "bg-[rgba(188,93,60,0.12)] text-[var(--accent-deep)]", label: "Processing" },
  indexed: { style: "bg-[rgba(29,107,76,0.12)] text-[var(--success)]", label: "Ready" },
  failed: { style: "bg-[rgba(159,47,47,0.12)] text-[var(--danger)]", label: "Failed" },
};

export function StatusPill({ status }: StatusPillProps) {
  const config = STATUS_CONFIG[status] ?? {
    style: "bg-[rgba(21,37,52,0.08)] text-[var(--muted)]",
    label: status,
  };

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${config.style}`}>
      {config.label}
    </span>
  );
}