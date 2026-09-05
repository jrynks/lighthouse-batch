import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import {
  EMPTY_CATEGORIES,
  EMPTY_METRICS,
  SCHEMA,
  type Strategy,
  type UrlResult,
} from "./types";
import { parseReport } from "./parse";

const AuditInput = z.object({
  url: z.string().min(1).max(2048),
  strategy: z.enum(["mobile", "desktop"]),
  categories: z.array(z.string()).min(1),
  timeoutSec: z.number().int().min(10).max(180).optional(),
});

function emptyResult(
  url: string,
  strategy: Strategy,
  status: UrlResult["status"],
  error: string | null,
): UrlResult {
  return {
    schema: SCHEMA,
    url,
    strategy,
    source: null,
    categories: { ...EMPTY_CATEGORIES },
    metrics: { ...EMPTY_METRICS },
    fetched_at: new Date().toISOString(),
    status,
    error,
    raw_path: null,
  };
}

function fromPayload(
  url: string,
  strategy: Strategy,
  source: UrlResult["source"],
  payload: unknown,
  categories: string[],
): UrlResult {
  const parsed = parseReport(payload, categories);
  if (!parsed) {
    return emptyResult(
      url,
      strategy,
      "FAILED",
      "report did not contain a Lighthouse result; scores not invented",
    );
  }
  return {
    schema: SCHEMA,
    url,
    strategy,
    source,
    categories: parsed.categories,
    metrics: parsed.metrics,
    fetched_at: new Date().toISOString(),
    status: "OK",
    error: null,
    raw_path: null,
  };
}

export const getDoctor = createServerFn({ method: "GET" }).handler(async () => {
  const { findChrome, findLighthouse } = await import("./local.server");
  const key = Boolean(process.env.PSI_API_KEY && process.env.PSI_API_KEY.trim());
  return {
    schema: "lighthouse-batch/v1-doctor",
    psi_key_configured: key,
    lighthouse: Boolean(findLighthouse()),
    chromium: Boolean(findChrome()),
    default_strategy: "mobile" as const,
  };
});

export const auditUrl = createServerFn({ method: "POST" })
  .validator((data) => AuditInput.parse(data))
  .handler(async ({ data }): Promise<UrlResult> => {
    const { assertPublicHttpUrl } = await import("./ssrf");
    const { fetchPsiWithRetry, PsiRequestError } = await import("./psi.server");
    const { findLighthouse, runLocalLighthouse } = await import("./local.server");

    const timeoutSec = data.timeoutSec ?? 120;
    const strategy = data.strategy;
    const requested = data.url.trim();
    let url: string;
    try {
      url = await assertPublicHttpUrl(requested);
    } catch (err) {
      return emptyResult(
        requested,
        strategy,
        "SKIPPED",
        err instanceof Error ? err.message : "invalid URL",
      );
    }

    const apiKey = process.env.PSI_API_KEY?.trim() || "";
    const errors: string[] = [];

    if (apiKey) {
      try {
        const payload = await fetchPsiWithRetry({
          url,
          strategy,
          categories: data.categories,
          apiKey,
          timeoutSec,
        });
        return fromPayload(requested, strategy, "psi", payload, data.categories);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "PSI failed";
        errors.push(`psi: ${msg}`);
        const fallback = err instanceof PsiRequestError ? err.fallback : true;
        if (!fallback) {
          return emptyResult(requested, strategy, "FAILED", errors.join("; "));
        }
      }
    }

    if (findLighthouse()) {
      try {
        const payload = await runLocalLighthouse({
          url,
          strategy,
          categories: data.categories,
          timeoutSec,
        });
        return fromPayload(requested, strategy, "local_lighthouse", payload, data.categories);
      } catch (err) {
        errors.push(`local_lighthouse: ${err instanceof Error ? err.message : "failed"}`);
      }
    } else if (!apiKey) {
      errors.push("no PSI API key configured and lighthouse CLI not found");
    }

    return emptyResult(
      requested,
      strategy,
      "FAILED",
      errors.join("; ") || "audit produced no report",
    );
  });

export const importReport = createServerFn({ method: "POST" })
  .validator((data) =>
    z
      .object({
        url: z.string().min(1).max(2048),
        strategy: z.enum(["mobile", "desktop"]),
        payload: z.unknown(),
        categories: z.array(z.string()).min(1),
      })
      .parse(data),
  )
  .handler(async ({ data }): Promise<UrlResult> => {
    const source =
      data.payload &&
      typeof data.payload === "object" &&
      "lighthouseResult" in (data.payload as object)
        ? "psi"
        : "local_lighthouse";
    return fromPayload(data.url, data.strategy, source, data.payload, data.categories);
  });
