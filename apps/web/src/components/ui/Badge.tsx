const TONES = {
  alta: "bg-danger-soft text-danger",
  media: "bg-warn-soft text-warn",
  info: "bg-info-soft text-info",
  ok: "bg-lexi-soft text-lexi-dark",
} as const;

export function Badge({ tone, children }: { tone: keyof typeof TONES; children: React.ReactNode }) {
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONES[tone]}`}>{children}</span>;
}
