import { useEffect, useMemo, useRef, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { AuditForm, type CatState } from "@/components/audit-form";
import { ResultsLedger } from "@/components/results-ledger";
import { Button } from "@/components/ui/button";
import { auditUrl, getDoctor, importReport } from "@/lib/audit/actions";
import { parseUrlLines, mapPool, lhCategories } from "@/lib/audit/client-urls";
import { loadRuns, saveRun, type StoredRun } from "@/lib/audit/history";
import { CATEGORY_META, type Strategy, type UrlResult } from "@/lib/audit/types";
import { Download } from "lucide-react";

const DEFAULT_URLS = "https://example.com\nhttps://example.com/404";

export function AuditApp() {
  const [urlsText, setUrlsText] = useState(DEFAULT_URLS);
  const [strategy, setStrategy] = useState<Strategy>("mobile");
  const [cats, setCats] = useState<CatState>({
    performance: true,
    accessibility: true,
    best_practices: true,
    seo: true,
  });
  const [running, setRunning] = useState(false);
  const [pending, setPending] = useState<string[]>([]);
  const [results, setResults] = useState<UrlResult[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [doctor, setDoctor] = useState<{
    psi_key_configured: boolean;
    lighthouse: boolean;
    chromium: boolean;
  } | null>(null);
  const [history, setHistory] = useState<StoredRun[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const stopRef = useRef(false);

  useEffect(() => {
    setHistory(loadRuns());
    getDoctor()
      .then(setDoctor)
      .catch(() => setDoctor({ psi_key_configured: false, lighthouse: false, chromium: false }));
  }, []);

  const averages = useMemo(() => {
    const ok = results.filter((r) => r.status === "OK");
    if (!ok.length) return null;
    const out: Record<string, number> = {};
    for (const meta of CATEGORY_META) {
      const vals = ok
        .map((r) => r.categories[meta.key])
        .filter((v): v is number => typeof v === "number");
      if (vals.length) out[meta.key] = Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
    }
    return Object.keys(out).length ? out : null;
  }, [results]);

  async function run() {
    const urls = parseUrlLines(urlsText);
    if (!urls.length) {
      setNotice("No URLs to audit (empty input).");
      return;
    }
    const categories = lhCategories(cats);
    stopRef.current = false;
    setRunning(true);
    setNotice(null);
    setResults([]);
    setSelected(null);
    setPending(urls);

    const slots: (UrlResult | null)[] = urls.map(() => null);
    await mapPool(
      urls,
      2,
      async (url, index) => {
        const row = await auditUrl({ data: { url, strategy, categories, timeoutSec: 120 } });
        const tagged = { ...row, url };
        slots[index] = tagged;
        setPending((p) => p.filter((u) => u !== url));
        setResults(slots.filter((r): r is UrlResult => r !== null));
        return tagged;
      },
      () => stopRef.current,
    );

    const final = slots.filter((r): r is UrlResult => r !== null);
    setResults(final);
    setPending([]);
    setRunning(false);
    const runRec: StoredRun = {
      id: crypto.randomUUID(),
      generated_at: new Date().toISOString(),
      strategy,
      results: final,
    };
    saveRun(runRec);
    setHistory(loadRuns());
    const ok = final.filter((r) => r.status === "OK").length;
    setNotice(`${ok} ok · ${final.length - ok} failed or skipped. Scores from live reports only.`);
  }

  async function onImport(file: File) {
    try {
      const text = await file.text();
      const payload = JSON.parse(text) as unknown;
      const url = parseUrlLines(urlsText)[0] ?? "imported://report";
      const row = await importReport({
        data: { url, strategy, payload, categories: lhCategories(cats) },
      });
      setResults([row]);
      setPending([]);
      setSelected(row.url);
      setNotice(
        row.status === "OK"
          ? "Imported a real Lighthouse/PSI report."
          : row.error ?? "Could not parse report; scores not invented.",
      );
    } catch {
      setNotice("That file is not JSON. Scores were not invented.");
    }
  }

  function downloadSummary() {
    const body = {
      schema: "lighthouse-batch/v1-summary",
      generated_at: new Date().toISOString(),
      strategy,
      total: results.length,
      ok: results.filter((r) => r.status === "OK").length,
      failed: results.filter((r) => r.status === "FAILED").length,
      skipped: results.filter((r) => r.status === "SKIPPED").length,
      results: results.map((r) => ({
        url: r.url,
        status: r.status,
        categories: r.categories,
        source: r.source,
      })),
      ...(averages ? { averages } : {}),
    };
    const blob = new Blob([JSON.stringify(body, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `summary-${new Date().toISOString().replace(/[:.]/g, "").slice(0, 15)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-5xl flex-col gap-8 px-4 py-8 sm:px-6 sm:py-12">
      <SiteHeader doctor={doctor} />
      <AuditForm
        urlsText={urlsText}
        onUrlsText={setUrlsText}
        strategy={strategy}
        onStrategy={setStrategy}
        cats={cats}
        onToggleCat={(k) => setCats((c) => ({ ...c, [k]: !c[k] }))}
        running={running}
        onRun={run}
        onImport={onImport}
      />
      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-[11px] uppercase tracking-[0.18em] text-muted">Results</h2>
            {averages ? (
              <p className="mt-1 font-mono text-sm tabular-nums text-muted">
                avg{" "}
                {CATEGORY_META.map((c) =>
                  averages[c.key] != null ? `${c.short} ${averages[c.key]}` : null,
                )
                  .filter(Boolean)
                  .join("   ")}
              </p>
            ) : (
              <p className="mt-1 text-sm text-subtle">Averages omitted until a run has numeric OK scores.</p>
            )}
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={!results.length}
            onClick={downloadSummary}
          >
            <Download />
            Summary JSON
          </Button>
        </div>
        <ResultsLedger
          results={results}
          pending={pending}
          selected={selected}
          onSelect={(url) => setSelected((s) => (s === url ? null : url))}
        />
        {notice ? <p className="text-sm text-muted">{notice}</p> : null}
      </section>
      {history.length ? (
        <section>
          <h2 className="text-[11px] uppercase tracking-[0.18em] text-muted">Recent runs</h2>
          <ul className="mt-3 divide-y divide-border">
            {history.slice(0, 6).map((run) => (
              <li key={run.id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 py-3 text-left"
                  onClick={() => {
                    setResults(run.results);
                    setPending([]);
                    setStrategy(run.strategy);
                    setNotice(`Restored run from ${run.generated_at}`);
                  }}
                >
                  <span className="font-mono text-sm tabular-nums text-muted">
                    {run.generated_at.replace("T", " ").replace(/\..+/, "")}
                  </span>
                  <span className="text-sm text-subtle">
                    {run.results.length} URL{run.results.length === 1 ? "" : "s"} · {run.strategy}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <footer className="mt-auto border-t border-border pt-6 text-xs leading-relaxed text-subtle">
        Audits the URLs you provide — no crawl. PSI is used when a key is configured;
        otherwise local Lighthouse against headless Chrome. Failed reports stay failed.
      </footer>
    </div>
  );
}
