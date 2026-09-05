import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/cn";
import type { Strategy } from "@/lib/audit/types";
import { Loader2, Play } from "lucide-react";

const CATS = [
  { key: "performance", label: "Perf" },
  { key: "accessibility", label: "A11y" },
  { key: "best_practices", label: "BP" },
  { key: "seo", label: "SEO" },
] as const;

export type CatState = Record<(typeof CATS)[number]["key"], boolean>;

export function AuditForm({
  urlsText,
  onUrlsText,
  strategy,
  onStrategy,
  cats,
  onToggleCat,
  running,
  onRun,
  onImport,
}: {
  urlsText: string;
  onUrlsText: (v: string) => void;
  strategy: Strategy;
  onStrategy: (s: Strategy) => void;
  cats: CatState;
  onToggleCat: (k: keyof CatState) => void;
  running: boolean;
  onRun: () => void;
  onImport: (file: File) => void;
}) {
  return (
    <section className="rounded-xl bg-bg-elevated p-4 shadow-[var(--shadow-border)] sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor="urls" className="text-[11px] uppercase tracking-[0.18em] text-muted">
          URLs
        </label>
        <span className="text-[11px] text-subtle">one per line · # comments ignored</span>
      </div>
      <Textarea
        id="urls"
        value={urlsText}
        onChange={(e) => onUrlsText(e.target.value)}
        spellCheck={false}
        placeholder={"https://example.com\nhttps://example.com/404"}
        className="mt-3 min-h-[8.5rem]"
        disabled={running}
      />
      <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div
            className="inline-flex rounded-md bg-bg p-1 shadow-[var(--shadow-border)]"
            role="group"
            aria-label="Strategy"
          >
            {(["mobile", "desktop"] as const).map((s) => (
              <button
                key={s}
                type="button"
                disabled={running}
                onClick={() => onStrategy(s)}
                className={cn(
                  "h-10 min-w-[5.5rem] rounded-sm px-3 text-sm capitalize transition-colors duration-150",
                  strategy === s ? "bg-primary text-primary-fg" : "text-muted hover:text-fg",
                )}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {CATS.map((c) => (
              <button
                key={c.key}
                type="button"
                disabled={running}
                onClick={() => onToggleCat(c.key)}
                className={cn(
                  "h-10 rounded-full px-3 text-[11px] uppercase tracking-[0.14em] shadow-[var(--shadow-border)] transition-colors duration-150",
                  cats[c.key] ? "bg-bg-subtle text-fg" : "text-subtle",
                )}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="inline-flex">
            <input
              type="file"
              accept="application/json,.json"
              className="sr-only"
              disabled={running}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onImport(file);
                e.currentTarget.value = "";
              }}
            />
            <span className="inline-flex h-11 cursor-pointer items-center rounded-md px-4 text-sm text-muted shadow-[var(--shadow-border)] hover:text-fg">
              Import JSON
            </span>
          </label>
          <Button type="button" onClick={onRun} disabled={running} className="min-w-[9.5rem]">
            {running ? <Loader2 className="animate-spin" /> : <Play />}
            {running ? "Running" : "Run audit"}
          </Button>
        </div>
      </div>
    </section>
  );
}
