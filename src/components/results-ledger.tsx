import { ScoreMark } from "@/components/score-mark";
import { Badge } from "@/components/ui/badge";
import { CATEGORY_META, type UrlResult } from "@/lib/audit/types";
import { cn } from "@/lib/cn";

function formatMetric(value: number | null, digits = 0, suffix = "") {
  if (value == null) return "—";
  return `${value.toFixed(digits)}${suffix}`;
}

export function ResultsLedger({
  results,
  pending,
  selected,
  onSelect,
}: {
  results: UrlResult[];
  pending: string[];
  selected: string | null;
  onSelect: (url: string) => void;
}) {
  if (results.length === 0 && pending.length === 0) {
    return (
      <div className="rounded-xl bg-bg-elevated px-6 py-16 text-center shadow-[var(--shadow-border)] sm:px-10">
        <p className="font-display text-3xl tracking-[-0.03em]">No run yet</p>
        <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-muted">
          Paste URLs and run an audit. Scores only appear after a real Lighthouse
          or PageSpeed report returns.
        </p>
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-3">
      {pending.map((url) => (
        <li
          key={`p-${url}`}
          className="rounded-xl bg-bg-elevated p-4 shadow-[var(--shadow-border)] sm:p-5"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm">{url}</p>
              <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-subtle shimmer bg-clip-text">
                Auditing
              </p>
            </div>
            <div className="flex justify-between sm:justify-end gap-3 opacity-40">
              {CATEGORY_META.map((c) => (
                <ScoreMark key={c.key} score={null} label={c.short} />
              ))}
            </div>
          </div>
        </li>
      ))}
      {results.map((row) => {
        const open = selected === row.url;
        return (
          <li key={row.url}>
            <button
              type="button"
              onClick={() => onSelect(row.url)}
              aria-label={`${row.url} ${row.status} perf ${row.categories.performance ?? "n/a"} a11y ${row.categories.accessibility ?? "n/a"} bp ${row.categories.best_practices ?? "n/a"} seo ${row.categories.seo ?? "n/a"}`}
              className={cn(
                "w-full rounded-xl bg-bg-elevated p-4 text-left shadow-[var(--shadow-border)] transition-[box-shadow] duration-150 sm:p-5",
                open && "shadow-[var(--shadow-border-hover)]",
              )}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm">{row.url}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Badge
                      className={
                        row.status === "OK"
                          ? "text-score-hi"
                          : row.status === "SKIPPED"
                            ? "text-muted"
                            : "text-score-lo"
                      }
                    >
                      {row.status}
                    </Badge>
                    {row.source ? <Badge>{row.source.replace("_", " ")}</Badge> : null}
                    <span className="text-[11px] uppercase tracking-[0.14em] text-subtle">
                      {row.strategy}
                    </span>
                  </div>
                  {row.error ? (
                    <p className="mt-2 text-sm text-score-lo">{row.error}</p>
                  ) : null}
                </div>
                <div className="flex justify-between sm:justify-end gap-3">
                  {CATEGORY_META.map((c) => (
                    <ScoreMark
                      key={c.key}
                      score={row.categories[c.key]}
                      label={c.short}
                    />
                  ))}
                </div>
              </div>
              {open ? (
                <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-border pt-4 sm:grid-cols-5">
                  <Metric label="LCP" value={formatMetric(row.metrics.lcp_ms, 0, " ms")} />
                  <Metric label="CLS" value={formatMetric(row.metrics.cls, 3)} />
                  <Metric label="TBT" value={formatMetric(row.metrics.tbt_ms, 0, " ms")} />
                  <Metric label="FCP" value={formatMetric(row.metrics.fcp_ms, 0, " ms")} />
                  <Metric label="SI" value={formatMetric(row.metrics.si, 0)} />
                </dl>
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-[0.14em] text-subtle">{label}</dt>
      <dd className="mt-1 font-mono text-sm tabular-nums">{value}</dd>
    </div>
  );
}
