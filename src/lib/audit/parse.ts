import {
  EMPTY_CATEGORIES,
  EMPTY_METRICS,
  type Categories,
  type Metrics,
} from "./types";

const TO_SCHEMA: Record<string, keyof Categories> = {
  performance: "performance",
  accessibility: "accessibility",
  "best-practices": "best_practices",
  seo: "seo",
};

const AUDIT_TO_METRIC: Record<string, keyof Metrics> = {
  "largest-contentful-paint": "lcp_ms",
  "cumulative-layout-shift": "cls",
  "total-blocking-time": "tbt_ms",
  "first-contentful-paint": "fcp_ms",
  "speed-index": "si",
};

export function extractLhr(payload: unknown): Record<string, unknown> | null {
  if (!payload || typeof payload !== "object") return null;
  const obj = payload as Record<string, unknown>;
  const inner = obj.lighthouseResult;
  if (inner && typeof inner === "object") {
    const lhr = inner as Record<string, unknown>;
    if ("categories" in lhr || "audits" in lhr || lhr.lighthouseVersion) return lhr;
  }
  if ("categories" in obj || obj.lighthouseVersion) return obj;
  return null;
}

export function scoreTo100(raw: unknown): number | null {
  if (raw === null || raw === undefined || typeof raw === "boolean") return null;
  if (typeof raw !== "number" || Number.isNaN(raw)) return null;
  if (raw < 0 || raw > 1) return null;
  return Math.round(raw * 1000) / 10;
}

function numericOrNone(raw: unknown): number | null {
  if (raw === null || raw === undefined || typeof raw === "boolean") return null;
  if (typeof raw !== "number" || Number.isNaN(raw)) return null;
  return raw;
}

export function parseReport(
  payload: unknown,
  wanted?: string[],
): { categories: Categories; metrics: Metrics } | null {
  const lhr = extractLhr(payload);
  if (!lhr) return null;

  const catsRaw =
    lhr.categories && typeof lhr.categories === "object"
      ? (lhr.categories as Record<string, unknown>)
      : {};
  const categories: Categories = { ...EMPTY_CATEGORIES };
  const wantedSet = wanted ? new Set(wanted) : null;

  for (const [lhId, schemaKey] of Object.entries(TO_SCHEMA)) {
    if (wantedSet && !wantedSet.has(lhId)) {
      categories[schemaKey] = null;
      continue;
    }
    const entry = catsRaw[lhId];
    if (!entry || typeof entry !== "object") {
      categories[schemaKey] = null;
      continue;
    }
    categories[schemaKey] = scoreTo100((entry as { score?: unknown }).score);
  }

  const auditsRaw =
    lhr.audits && typeof lhr.audits === "object"
      ? (lhr.audits as Record<string, unknown>)
      : {};
  const metrics: Metrics = { ...EMPTY_METRICS };
  for (const [auditId, metricKey] of Object.entries(AUDIT_TO_METRIC)) {
    const entry = auditsRaw[auditId];
    if (!entry || typeof entry !== "object") {
      metrics[metricKey] = null;
      continue;
    }
    metrics[metricKey] = numericOrNone(
      (entry as { numericValue?: unknown }).numericValue,
    );
  }

  return { categories, metrics };
}
