export function parseUrlLines(text: string): string[] {
  const urls: string[] = [];
  const seen = new Set<string>();
  for (const line of text.split(/\r?\n/)) {
    const stripped = line.trim();
    if (!stripped || stripped.startsWith("#")) continue;
    if (seen.has(stripped)) continue;
    seen.add(stripped);
    urls.push(stripped);
  }
  return urls;
}

export async function mapPool<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
  shouldStop?: () => boolean,
): Promise<R[]> {
  const out = new Array<R>(items.length);
  let next = 0;
  async function worker() {
    while (true) {
      if (shouldStop?.()) return;
      const i = next++;
      if (i >= items.length) return;
      out[i] = await fn(items[i] as T, i);
    }
  }
  const n = Math.max(1, Math.min(limit, items.length));
  await Promise.all(Array.from({ length: n }, () => worker()));
  return out;
}

export function lhCategories(selected: {
  performance: boolean;
  accessibility: boolean;
  best_practices: boolean;
  seo: boolean;
}): string[] {
  const out: string[] = [];
  if (selected.performance) out.push("performance");
  if (selected.accessibility) out.push("accessibility");
  if (selected.best_practices) out.push("best-practices");
  if (selected.seo) out.push("seo");
  return out.length ? out : ["performance", "accessibility", "best-practices", "seo"];
}
