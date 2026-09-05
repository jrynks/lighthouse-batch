import { cn } from "@/lib/cn";

function band(score: number | null): "hi" | "mid" | "lo" | "none" {
  if (score == null) return "none";
  if (score >= 90) return "hi";
  if (score >= 50) return "mid";
  return "lo";
}

const STROKE: Record<ReturnType<typeof band>, string> = {
  hi: "stroke-score-hi",
  mid: "stroke-score-mid",
  lo: "stroke-score-lo",
  none: "stroke-border-strong",
};

const TEXT: Record<ReturnType<typeof band>, string> = {
  hi: "text-score-hi",
  mid: "text-score-mid",
  lo: "text-score-lo",
  none: "text-subtle",
};

export function ScoreMark({
  score,
  label,
  size = 56,
}: {
  score: number | null;
  label: string;
  size?: number;
}) {
  const b = band(score);
  const r = 18;
  const c = 2 * Math.PI * r;
  const pct = score == null ? 0 : Math.max(0, Math.min(100, score)) / 100;
  return (
    <div className="flex flex-col items-center gap-1.5 min-w-[3.5rem]">
      <div className="relative" style={{ width: size, height: size }}>
        <svg viewBox="0 0 44 44" className="size-full -rotate-90" aria-hidden="true">
          <circle
            cx="22"
            cy="22"
            r={r}
            fill="none"
            className="stroke-border"
            strokeWidth="3"
          />
          <circle
            cx="22"
            cy="22"
            r={r}
            fill="none"
            className={cn(STROKE[b], "transition-[stroke-dashoffset] duration-[400ms] ease-[cubic-bezier(0.22,1,0.36,1)]")}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - pct)}
          />
        </svg>
        <span
          className={cn(
            "absolute inset-0 grid place-items-center font-mono text-[13px] tabular-nums",
            TEXT[b],
          )}
        >
          {score == null ? "—" : Math.round(score)}
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-[0.14em] text-subtle">{label}</span>
    </div>
  );
}

export function scoreBand(score: number | null) {
  return band(score);
}
