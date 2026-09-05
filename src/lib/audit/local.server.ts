import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  process.env.LIGHTHOUSE_CHROME_PATH,
  "/opt/pw-browsers/chromium-1234/chrome-linux64/chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter((p): p is string => Boolean(p));

const LH_CANDIDATES = [
  process.env.LIGHTHOUSE_BIN,
  join(process.cwd(), "node_modules/.bin/lighthouse"),
  "/workspace/node_modules/.bin/lighthouse",
].filter((p): p is string => Boolean(p));

export function findChrome(): string | null {
  for (const p of CHROME_CANDIDATES) {
    if (existsSync(p)) return p;
  }
  return null;
}

export function findLighthouse(): string | null {
  for (const p of LH_CANDIDATES) {
    if (existsSync(p)) return p;
  }
  return null;
}

export async function runLocalLighthouse(opts: {
  url: string;
  strategy: "mobile" | "desktop";
  categories: string[];
  timeoutSec: number;
}): Promise<unknown> {
  const bin = findLighthouse();
  if (!bin) throw new Error("lighthouse CLI not found");
  const chrome = findChrome();
  const dir = await mkdtemp(join(tmpdir(), "lh-batch-"));
  const outPath = join(dir, "report.json");
  const args = [
    opts.url,
    "--output=json",
    `--output-path=${outPath}`,
    "--quiet",
    "--disable-full-page-screenshot",
    "--no-enable-error-reporting",
    `--only-categories=${opts.categories.join(",")}`,
    "--chrome-flags=--headless --no-sandbox --disable-gpu --disable-dev-shm-usage",
  ];
  if (opts.strategy === "desktop") {
    args.push(
      "--form-factor=desktop",
      "--screenEmulation.mobile=false",
      "--preset=desktop",
    );
  } else {
    args.push("--form-factor=mobile", "--screenEmulation.mobile=true");
  }

  const env = { ...process.env };
  if (chrome) {
    env.CHROME_PATH = chrome;
    env.LIGHTHOUSE_CHROMIUM_PATH = chrome;
  }

  try {
    const { code, stderr } = await spawnOnce(bin, args, {
      env,
      timeoutMs: opts.timeoutSec * 1000,
    });
    if (!existsSync(outPath)) {
      throw new Error(
        stderr.trim()
          ? `local lighthouse failed: ${stderr.trim().slice(-800)}`
          : `local lighthouse exited ${code} without a report`,
      );
    }
    const raw = await readFile(outPath, "utf8");
    return JSON.parse(raw) as unknown;
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

function spawnOnce(
  cmd: string,
  args: string[],
  opts: { env: NodeJS.ProcessEnv; timeoutMs: number },
): Promise<{ code: number | null; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      env: opts.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString("utf8");
      if (stderr.length > 4000) stderr = stderr.slice(-4000);
    });
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`local lighthouse timed out after ${opts.timeoutMs}ms`));
    }, opts.timeoutMs);
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stderr });
    });
  });
}
