/**
 * Small, dependency-free boundaries shared by the browser evidence tools.
 * Stored records are written as bytes, then renamed into place; identity is
 * always calculated from those final bytes.
 */
import { createHash } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve } from "node:path";

export const EXIT = Object.freeze({ OK: 0, INPUT: 2, CAPABILITY: 3, EVIDENCE: 4, TIMEOUT: 5 });

export function sha256(value) {
  const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

export function canonicalJson(value) {
  return `${JSON.stringify(value, (_key, item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    return Object.keys(item).sort().reduce((out, key) => {
      out[key] = item[key];
      return out;
    }, {});
  }, 2)}\n`;
}

export async function writeJsonAtomic(path, value) {
  const bytes = Buffer.from(canonicalJson(value), "utf8");
  await mkdir(dirname(path), { recursive: true });
  const temporary = `${path}.tmp-${process.pid}-${Date.now()}`;
  await writeFile(temporary, bytes, { flag: "wx" });
  await rename(temporary, path);
  return { path, hash: sha256(bytes), bytes: bytes.length };
}

export async function readJson(path) {
  const bytes = await readFile(path);
  try {
    return { value: JSON.parse(bytes.toString("utf8")), bytes, hash: sha256(bytes) };
  } catch (error) {
    throw inputError(`invalid JSON in ${path}: ${error.message}`, "/");
  }
}

export function inputError(message, pointer = "/") {
  const error = new Error(message);
  error.code = "invalid-input";
  error.pointer = pointer;
  return error;
}

export function evidenceError(message, pointer = "/") {
  const error = new Error(message);
  error.code = "evidence-failure";
  error.pointer = pointer;
  return error;
}

export function capabilityError(message, pointer = "/") {
  const error = new Error(message);
  error.code = "capability-unverified";
  error.pointer = pointer;
  return error;
}

export function timeoutError(message, pointer = "/") {
  const error = new Error(message);
  error.code = "timeout-process-loss";
  error.pointer = pointer;
  return error;
}

export function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith("--")) throw inputError(`unexpected argument ${item}`);
    const key = item.slice(2).replaceAll("-", "_");
    if (!key) throw inputError("empty argument name");
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

export function requireObject(value, pointer = "/") {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw inputError(`expected object, observed ${JSON.stringify(value)}`, pointer);
  }
  return value;
}

export function requireString(value, pointer) {
  if (typeof value !== "string" || value.length === 0) {
    throw inputError(`expected non-empty string, observed ${JSON.stringify(value)}`, pointer);
  }
  return value;
}

export function requireFiniteNumber(value, pointer) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw inputError(`expected finite number, observed ${JSON.stringify(value)}`, pointer);
  }
  return value;
}

export function ensureContained(root, candidate, pointer = "/") {
  const base = resolve(root);
  const target = resolve(candidate);
  const rel = relative(base, target);
  if (isAbsolute(rel) || rel === ".." || rel.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`)) {
    throw inputError(`path escapes root: ${candidate}`, pointer);
  }
  return target;
}

export function nowIso() {
  return new Date().toISOString();
}

export function makeHeader({ kind, id, artifactCommit, producer, inputs = {}, environment = {}, status = "draft", gaps = [], invalidates = [] }) {
  requireString(kind, "/kind");
  requireString(id, "/id");
  requireString(artifactCommit, "/artifact_commit");
  if (typeof producer !== "string" && (!producer || typeof producer !== "object" || Array.isArray(producer))) {
    throw inputError("producer must be a name or object with a name", "/producer");
  }
  const inputRows = Array.isArray(inputs) ? inputs : Object.entries(inputs).map(([name, sha256Value]) => ({ name, sha256: sha256Value }));
  if (!Array.isArray(inputRows) || inputRows.some(item => !item || typeof item.name !== "string" || !/^sha256:[0-9a-f]{64}$/.test(item.sha256))) {
    throw inputError("inputs must be an array of {name, sha256} identities", "/inputs");
  }
  if (!["draft", "ready", "complete", "failed", "invalid", "unverified", "superseded"].includes(status)) {
    throw inputError(`invalid record status ${status}`, "/status");
  }
  const producerValue = typeof producer === "string" ? { name: producer } : producer;
  if (!producerValue || typeof producerValue.name !== "string" || !producerValue.name) throw inputError("producer must include a name", "/producer");
  const environmentValue = { host: "codex", os: `${process.platform}-${process.arch}`, tools: [], ...environment };
  if (!Array.isArray(environmentValue.tools)) throw inputError("environment.tools must be an array", "/environment/tools");
  return {
    schema_version: "1.0.0",
    kind,
    id,
    artifact_commit: artifactCommit,
    created_at: nowIso(),
    producer: producerValue,
    inputs: inputRows,
    environment: environmentValue,
    status,
    gaps,
    invalidates,
  };
}

export function resultFromError(error) {
  const code = error?.code || "invalid-input";
  const exitCode = code === "capability-unverified" ? EXIT.CAPABILITY
    : code === "evidence-failure" ? EXIT.EVIDENCE
      : code === "timeout-process-loss" ? EXIT.TIMEOUT : EXIT.INPUT;
  return {
    exitCode,
    result: {
      status: code === "capability-unverified" ? "unverified" : "error",
      error: { code, pointer: error?.pointer || "/", message: error?.message || String(error) },
    },
  };
}

export function printResult(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
}
