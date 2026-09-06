/**
 * Package-owned adapter for the documented browser_harness JSONL protocol.
 * The outside probe supplies an already-supervised production URL; this
 * adapter keeps the harness's ordinary stdin commands and stores its session.
 */
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { readJson, inputError, nowIso, parseArgs, resultFromError } from "./_common.mjs";
import { runHarness } from "./browser_harness.mjs";

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.config) throw inputError("--config is required", "/config");
  const { value: config } = await readJson(resolve(args.config));
  if (!config.server || config.server.external !== true) throw inputError("outside harness requires an externally supervised server", "/server/external");
  const session = await runHarness(config);
  process.stdout.write(`${JSON.stringify({
    status: "observed", artifact_commit: config.artifact_commit, observed_at: session.ended_at || nowIso(),
    session_id: session.id, session_path: config.session_out || null, transcript_hash: session.transcript_hash,
    transcript_lines: session.transcript.length, classification: session.classification, source: session.source,
  })}\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { main };
