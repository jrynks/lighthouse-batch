import { isIP } from "node:net";
import dns from "node:dns/promises";

function isPrivateIp(ip: string): boolean {
  const v = ip.toLowerCase().replace(/^::ffff:/, "");
  if (v === "127.0.0.1" || v === "::1" || v === "0.0.0.0") return true;
  if (v.startsWith("10.")) return true;
  if (v.startsWith("127.")) return true;
  if (v.startsWith("169.254.")) return true;
  if (v.startsWith("192.168.")) return true;
  if (v.startsWith("0.")) return true;
  const m = /^172\.(\d+)\./.exec(v);
  if (m) {
    const n = Number(m[1]);
    if (n >= 16 && n <= 31) return true;
  }
  if (v.startsWith("fc") || v.startsWith("fd") || v.startsWith("fe80")) return true;
  return false;
}

const BLOCKED_HOSTS = new Set([
  "localhost",
  "metadata.google.internal",
  "metadata",
]);

export async function assertPublicHttpUrl(raw: string): Promise<string> {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("not an http(s) URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("not an http(s) URL");
  }
  if (url.username || url.password) {
    throw new Error("URLs with credentials are not allowed");
  }
  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (BLOCKED_HOSTS.has(host) || host.endsWith(".localhost")) {
    throw new Error("private or loopback hosts are not allowed");
  }
  if (isIP(host)) {
    if (isPrivateIp(host)) throw new Error("private IP addresses are not allowed");
    return url.toString();
  }
  let addrs: string[] = [];
  try {
    const resolved = await dns.lookup(host, { all: true });
    addrs = resolved.map((r) => r.address);
  } catch {
    throw new Error(`could not resolve host: ${host}`);
  }
  if (addrs.length === 0) throw new Error(`could not resolve host: ${host}`);
  if (addrs.some(isPrivateIp)) {
    throw new Error("host resolves to a private address");
  }
  return url.toString();
}
