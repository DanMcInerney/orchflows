/**
 * Serve one already-built production directory and remain supervised until
 * the outside probe closes it. Every request is confined to that directory,
 * including real-path checks that reject symlink escapes.
 */
import { createServer } from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { dirname, extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { ensureContained, evidenceError, inputError, nowIso, parseArgs, readJson, resultFromError, sha256 } from "./_common.mjs";
import { inventory, validateConfig } from "./outside_build.mjs";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const MIME = Object.freeze({ ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8", ".map": "application/json; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".webp": "image/webp", ".woff": "font/woff", ".woff2": "font/woff2", ".wasm": "application/wasm" });

function routePath(root, pathname) {
  let decoded;
  try { decoded = decodeURIComponent(pathname); }
  catch { throw evidenceError("production server received an invalid URL path", "/server/url"); }
  if (!decoded.startsWith("/") || decoded.includes("\\") || decoded.split("/").includes("..")) throw evidenceError("production server rejected a path outside the output directory", "/server/url");
  const candidate = resolve(root, `.${decoded === "/" ? "/index.html" : decoded}`);
  return ensureContained(root, candidate, "/server/url");
}

async function staticServer(config, { workspace, artifactCommit, outputHash } = {}) {
  const checked = validateConfig(config);
  if (!workspace || typeof workspace !== "string") throw inputError("joined workspace is required", "/workspace");
  // Compare physical paths on both sides (workspace aliases are valid roots).
  const root = await realpath(resolve(workspace));
  const outputPath = ensureContained(root, resolve(root, checked.server.output_dir), "/server/output_dir");
  const resolvedOutput = await realpath(outputPath);
  ensureContained(root, resolvedOutput, "/server/output_dir");
  const observed = await inventory(root, resolvedOutput);
  if (outputHash && observed.sha256 !== outputHash) throw evidenceError(`server output hash differs from the production build: expected ${outputHash}, observed ${observed.sha256}`, "/server/output_dir");
  const host = checked.server.host || "127.0.0.1";
  const port = checked.server.port === undefined ? 0 : checked.server.port;
  const readyPath = checked.server.ready_path;
  if (typeof readyPath !== "string" || !readyPath.startsWith("/")) throw inputError("server.ready_path must begin with /", "/server/ready_path");
  const server = createServer(async (request, response) => {
    try {
      const pathname = new URL(request.url || "/", "http://127.0.0.1").pathname;
      const filePath = routePath(resolvedOutput, pathname);
      const canonical = await realpath(filePath);
      ensureContained(resolvedOutput, canonical, "/server/url");
      const metadata = await stat(canonical);
      if (!metadata.isFile()) { response.writeHead(404); response.end("Not Found"); return; }
      const bytes = await readFile(canonical);
      response.writeHead(200, { "Content-Type": MIME[extname(canonical).toLowerCase()] || "application/octet-stream", "Content-Length": bytes.length, "Cache-Control": "no-store" });
      response.end(bytes);
    } catch (error) {
      const status = error?.code === "evidence-failure" ? 400 : error?.code === "ENOENT" ? 404 : 500;
      response.writeHead(status, { "Content-Type": "text/plain; charset=utf-8" });
      response.end(status === 404 ? "Not Found" : "Request rejected");
    }
  });
  const address = await new Promise((resolvePromise, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => resolvePromise(server.address()));
  });
  const actualHost = typeof address === "object" && address ? address.address : host;
  const actualPort = typeof address === "object" && address ? address.port : port;
  const origin = `http://${actualHost.includes(":") ? `[${actualHost}]` : actualHost}:${actualPort}`;
  const url = `${origin}${readyPath}`;
  let readiness;
  try {
    const response = await fetch(url, { cache: "no-store" });
    const body = await response.arrayBuffer();
    readiness = { path: readyPath, status: response.status, bytes: body.byteLength, sha256: sha256(Buffer.from(body)) };
    if (response.status !== 200 || body.byteLength === 0) throw evidenceError(`production server readiness returned HTTP ${response.status}`, "/server/ready_path");
  } catch (error) {
    await new Promise(resolvePromise => server.close(() => resolvePromise()));
    throw error;
  }
  const ready = { status: "ready", artifact_commit: artifactCommit, observed_at: nowIso(), package_root: PACKAGE_ROOT, output: observed, address: { host: actualHost, port: actualPort, url: `${origin}/` }, readiness: { ...readiness, url } };
  process.stdout.write(`${JSON.stringify(ready)}\n`);
  return new Promise(resolvePromise => {
    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      server.close(() => { process.stdout.write(`${JSON.stringify({ status: "stopped", artifact_commit: artifactCommit, observed_at: nowIso(), pid: process.pid })}\n`); resolvePromise(); });
    };
    process.once("SIGINT", close);
    process.once("SIGTERM", close);
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.config || !args.workspace || !args.artifact_commit) throw inputError("--config, --workspace, and --artifact-commit are required");
  const { value: config } = await readJson(resolve(args.config));
  await staticServer(config, { workspace: resolve(args.workspace), artifactCommit: args.artifact_commit, outputHash: args.output_sha256 });
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { routePath, staticServer };
