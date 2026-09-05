export const SCHEMA = "lighthouse-batch/v1" as const;
export const SCHEMA_SUMMARY = "lighthouse-batch/v1-summary" as const;

export type Strategy = "mobile" | "desktop";
export type Source = "psi" | "local_lighthouse";
export type Status = "OK" | "FAILED" | "SKIPPED";

export type Categories = {
  performance: number | null;
  accessibility: number | null;
  best_practices: number | null;
  seo: number | null;
};

export type Metrics = {
  lcp_ms: number | null;
  cls: number | null;
  tbt_ms: number | null;
  fcp_ms: number | null;
  si: number | null;
};

export type UrlResult = {
  schema: typeof SCHEMA;
  url: string;
  strategy: Strategy;
  source: Source | null;
  categories: Categories;
  metrics: Metrics;
  fetched_at: string;
  status: Status;
  error: string | null;
  raw_path: string | null;
};

export type BatchSummary = {
  schema: typeof SCHEMA_SUMMARY;
  generated_at: string;
  strategy: Strategy;
  total: number;
  ok: number;
  failed: number;
  skipped: number;
  results: Array<{
    url: string;
    status: Status;
    categories: Categories;
    source: Source | null;
  }>;
  averages?: Partial<Categories>;
};

export const EMPTY_CATEGORIES: Categories = {
  performance: null,
  accessibility: null,
  best_practices: null,
  seo: null,
};

export const EMPTY_METRICS: Metrics = {
  lcp_ms: null,
  cls: null,
  tbt_ms: null,
  fcp_ms: null,
  si: null,
};

export const CATEGORY_META = [
  { key: "performance" as const, short: "Perf", lh: "performance" },
  { key: "accessibility" as const, short: "A11y", lh: "accessibility" },
  { key: "best_practices" as const, short: "BP", lh: "best-practices" },
  { key: "seo" as const, short: "SEO", lh: "seo" },
];
