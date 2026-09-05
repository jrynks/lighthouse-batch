const PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed";

const PSI_CATEGORY: Record<string, string> = {
  performance: "PERFORMANCE",
  accessibility: "ACCESSIBILITY",
  "best-practices": "BEST_PRACTICES",
  seo: "SEO",
};

export class PsiRequestError extends Error {
  status: number | null;
  quota: boolean;
  fallback: boolean;
  retryAfter: number | null;

  constructor(
    message: string,
    opts: {
      status?: number | null;
      quota?: boolean;
      fallback?: boolean;
      retryAfter?: number | null;
    } = {},
  ) {
    super(message);
    this.name = "PsiRequestError";
    this.status = opts.status ?? null;
    this.quota = Boolean(opts.quota);
    this.fallback = Boolean(opts.fallback);
    this.retryAfter = opts.retryAfter ?? null;
  }
}

function quotaish(status: number | null, body: unknown): boolean {
  if (status === 429) return true;
  const text = JSON.stringify(body ?? "").toLowerCase();
  return (
    text.includes("quota") ||
    text.includes("rate limit") ||
    text.includes("resource_exhausted") ||
    text.includes("ratelimitexceeded")
  );
}

function errorMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const err = (body as { error?: unknown }).error;
  if (err && typeof err === "object" && typeof (err as { message?: unknown }).message === "string") {
    return (err as { message: string }).message;
  }
  if (typeof err === "string") return err;
  return null;
}

export async function fetchPsi(opts: {
  url: string;
  strategy: "mobile" | "desktop";
  categories: string[];
  apiKey: string;
  timeoutSec: number;
}): Promise<unknown> {
  const params = new URLSearchParams({
    url: opts.url,
    strategy: opts.strategy,
    key: opts.apiKey,
  });
  for (const cat of opts.categories) {
    params.append("category", PSI_CATEGORY[cat] ?? cat.toUpperCase());
  }

  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), opts.timeoutSec * 1000);
  let res: Response;
  try {
    res = await fetch(`${PSI_ENDPOINT}?${params.toString()}`, {
      signal: ac.signal,
      headers: { Accept: "application/json" },
    });
  } catch (err) {
    const aborted = err instanceof Error && err.name === "AbortError";
    throw new PsiRequestError(aborted ? "PSI timed out" : "PSI network error", {
      fallback: true,
    });
  } finally {
    clearTimeout(timer);
  }

  const retryAfterHeader = res.headers.get("retry-after");
  const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : null;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }

  if (!res.ok) {
    const quota = quotaish(res.status, body);
    const fallback = quota || res.status >= 500 || res.status === 401 || res.status === 403 || res.status === 429;
    throw new PsiRequestError(errorMessage(body) ?? `PSI HTTP ${res.status}`, {
      status: res.status,
      quota,
      fallback,
      retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
    });
  }

  if (!body || typeof body !== "object" || !("lighthouseResult" in body)) {
    throw new PsiRequestError("PSI response missing lighthouseResult", {
      status: res.status,
      fallback: false,
    });
  }
  return body;
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function fetchPsiWithRetry(opts: {
  url: string;
  strategy: "mobile" | "desktop";
  categories: string[];
  apiKey: string;
  timeoutSec: number;
}): Promise<unknown> {
  let last: PsiRequestError | null = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await fetchPsi(opts);
    } catch (err) {
      if (!(err instanceof PsiRequestError)) throw err;
      last = err;
      if (!err.fallback) throw err;
      const retryable = err.quota || err.status === 429 || (err.status ?? 0) >= 500;
      if (attempt < 2 && retryable) {
        const wait = err.retryAfter != null ? Math.min(err.retryAfter, 60) * 1000 : 2 ** attempt * 1000;
        await sleep(wait);
        continue;
      }
      throw err;
    }
  }
  throw last ?? new PsiRequestError("PSI failed", { fallback: true });
}
