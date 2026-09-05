import { Badge } from "@/components/ui/badge";

type Doctor = {
  psi_key_configured: boolean;
  lighthouse: boolean;
  chromium: boolean;
};

function Pill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-muted">
      <span
        className={
          ok
            ? "size-1.5 rounded-full bg-score-hi"
            : "size-1.5 rounded-full bg-subtle"
        }
        aria-hidden="true"
      />
      {label}
      <span className="text-subtle">{ok ? "on" : "off"}</span>
    </span>
  );
}

export function SiteHeader({ doctor }: { doctor: Doctor | null }) {
  return (
    <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="stagger-in">
        <p className="text-[11px] uppercase tracking-[0.22em] text-muted">
          lighthouse-batch
        </p>
        <h1 className="font-display text-[2.6rem] leading-[1.05] tracking-[-0.03em] sm:text-5xl">
          Site Audit
        </h1>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-muted">
          Real Lighthouse scores from PageSpeed Insights or local Chrome. Missing
          categories stay empty — never invented.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {doctor ? (
          <>
            <Pill ok={doctor.psi_key_configured} label="PSI key" />
            <Pill ok={doctor.lighthouse} label="Lighthouse" />
            <Pill ok={doctor.chromium} label="Chromium" />
          </>
        ) : (
          <Badge>checking tools</Badge>
        )}
      </div>
    </header>
  );
}
