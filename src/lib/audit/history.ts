import type { Strategy, UrlResult } from "./types";

const KEY = "site-audit:runs";
const MAX = 12;

export type StoredRun = {
  id: string;
  generated_at: string;
  strategy: Strategy;
  results: UrlResult[];
};

export function loadRuns(): StoredRun[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as StoredRun[]) : [];
  } catch {
    return [];
  }
}

export function saveRun(run: StoredRun) {
  if (typeof localStorage === "undefined") return;
  const next = [run, ...loadRuns().filter((r) => r.id !== run.id)].slice(0, MAX);
  localStorage.setItem(KEY, JSON.stringify(next));
}

export function clearRuns() {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(KEY);
}
