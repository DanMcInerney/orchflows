import { createHash } from "node:crypto";
import { readdir, readFile, mkdir, writeFile } from "node:fs/promises";
import { resolve, relative } from "node:path";
import { build } from "vite";
const root = process.cwd(), testBuild = process.argv.includes("--test"), output = testBuild ? "test-dist" : "dist";
async function walk(dir) {
  const out = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (["node_modules", "__pycache__"].includes(entry.name) || entry.name.endsWith(".blend1")) continue;
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) out.push(...await walk(path)); else out.push(path);
  }
  return out;
}
const files = [];
for (const dir of ["src", "scripts", "tests", "public", "assets/source"]) files.push(...await walk(resolve(root, dir)));
for (const name of ["index.html", "asset-preview.html", "package.json", "package-lock.json", "vite.config.js"]) files.push(resolve(root, name));
const source = [];
for (const path of files.sort()) source.push({ path: relative(root, path).replaceAll("\\", "/"), sha256: createHash("sha256").update(await readFile(path)).digest("hex") });
const digest = createHash("sha256").update(JSON.stringify(source)).digest("hex").slice(0, 12);
const id = `${testBuild ? "qa" : "release"}-${digest}`;
process.env.VITE_BUILD_ID = id;
process.env.VITE_TEST_BUILD = testBuild ? "1" : "0";
await build({ root, logLevel: "info", build: { outDir: output, emptyOutDir: true } });
const built = [];
let javascript = "";
for (const path of (await walk(resolve(root, output))).sort()) {
  const bytes = await readFile(path);
  built.push({ path: relative(root, path).replaceAll("\\", "/"), sha256: createHash("sha256").update(bytes).digest("hex") });
  if (path.endsWith(".js")) javascript += bytes.toString();
}
const adapterPresent = javascript.includes("__gameTest"), fixturesPresent = javascript.includes("boss-danger");
if (testBuild ? !adapterPresent || !fixturesPresent : adapterPresent || fixturesPresent) throw Error("Diagnostic isolation audit failed");
await mkdir(resolve(root, "evidence/builds"), { recursive: true });
await writeFile(resolve(root, `evidence/builds/${id}.json`), JSON.stringify({ id, sourceIdentity: `source-${digest}`, kind: testBuild ? "assisted-test" : "ordinary-release", created: new Date().toISOString(), diagnosticAudit: { adapterPresent, fixturesPresent }, source, built }, null, 2));
await writeFile(resolve(root, `notes/${testBuild ? "test-build-id" : "build-id"}.txt`), `${id}\n`);
console.log(`Frozen ${testBuild ? "test" : "release"} identity: ${id}`);
