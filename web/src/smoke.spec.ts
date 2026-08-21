// @ts-nocheck -- Playwright owns this Node-side harness; application code remains strict.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { spawn } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const executablePath = process.env.ORCHFLOWS_BROWSER_EXECUTABLE || undefined;
test.use({ launchOptions: executablePath ? { executablePath } : undefined });

let serverProcess;
let devProcess;
let stateRoot = "";
let origin = "";
const action = process.env.ORCHFLOWS_UI_ACTION || "smoke";
const apiOrigin = process.env.ORCHFLOWS_UI_API_ORIGIN || "";
const experienceMode = process.env.ORCHFLOWS_UI_EXPERIENCE === "1";

async function startVite() {
  const viteScript = resolve("node_modules", "vite", "bin", "vite.js");
  devProcess = spawn(process.execPath, [viteScript, "--host", "127.0.0.1", "--port", "0"], {
    cwd: process.cwd(), env: { ...process.env, ORCHFLOWS_UI_API_ORIGIN: apiOrigin }, stdio: ["ignore", "pipe", "pipe"]
  });
  origin = await new Promise((resolveOrigin, reject) => {
    let stderr = "";
    devProcess.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    devProcess.stdout.on("data", (chunk) => {
      const match = chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) resolveOrigin(match[0]);
    });
    devProcess.once("exit", (code) => reject(new Error(`vite exited ${code}: ${stderr}`)));
  });
}

test.beforeAll(async () => {
  if (action !== "smoke") {
    await startVite();
    return;
  }
  stateRoot = await mkdtemp(join(tmpdir(), "orchflows-smoke-"));
  await mkdir(join(stateRoot, "tickets"));
  await cp(resolve("tests", "fixtures", "ui", "run-gamma"), join(stateRoot, "tickets", "run-gamma"), { recursive: true });
  await cp(resolve("tests", "fixtures", "ui", "run-gamma"), join(stateRoot, "tickets", "run-delta"), { recursive: true });
  const objectivePath = join(stateRoot, "tickets", "run-gamma", "G1.md");
  const objectiveTicket = await readFile(objectivePath, "utf8");
  await writeFile(
    objectivePath,
    objectiveTicket.replace(
      "A ticket whose `## Verification` carries the five-column table shape, one\nrow of which escapes a pipe inside its evidence cell.",
      "A deliberately long workflow objective that must remain glanceable on the fleet dashboard while its complete canonical wording remains available on demand. ".repeat(35)
    ),
    "utf8"
  );
  const transcriptRoot = join(stateRoot, "transcripts");
  await cp(resolve("tests", "fixtures", "transcripts"), transcriptRoot, { recursive: true });
  const agentRoot = join(transcriptRoot, "-Users-dmcinerney-tools-alpha", "11111111-1111-4111-8111-111111111111", "subagents");
  for (let index = 20; index < 38; index += 1) {
    await writeFile(join(agentRoot, `agent-browser-${index}.meta.json`), JSON.stringify({
      agentType: "orch-worker", description: `Browser geometry agent ${index}`,
      toolUseId: `tool-browser-${index}`, spawnDepth: 1
    }), "utf8");
  }
  const frictionRoot = join(stateRoot, "friction");
  await mkdir(frictionRoot);
  await writeFile(join(frictionRoot, "2026-08.jsonl"), Array.from({ length: 130 }, (_, index) => JSON.stringify({
    ts: `2026-08-19T12:${String(index % 60).padStart(2, "0")}:00Z`,
    ...(index % 2 ? { category: "historical-browser-guard" } : {}),
    host: "fixture", observed: `Synthetic friction ${index + 1}`, expected: "A bounded initial feed"
  })).join("\n"), "utf8");
  serverProcess = spawn(process.env.ORCHFLOWS_PYTHON || "python", [
    "-u", "scripts/ui.py", "--root", stateRoot, "--transcripts", transcriptRoot, "--port", "0"
  ], { cwd: process.cwd(), stdio: ["ignore", "pipe", "pipe"] });
  origin = await new Promise((resolveOrigin, reject) => {
    let stderr = "";
    serverProcess.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    serverProcess.stdout.on("data", (chunk) => {
      const match = chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) resolveOrigin(match[0]);
    });
    serverProcess.once("exit", (code) => reject(new Error(`reader exited ${code}: ${stderr}`)));
  });
});

test.afterAll(async () => {
  serverProcess?.kill();
  devProcess?.kill();
  await rm(stateRoot, { recursive: true, force: true });
});

async function openManifestIdentity(page, identity, width, height) {
  await page.setViewportSize({ width, height });
  await page.goto(`${origin}${identity.path}`);
  await expect(page.locator(".foundation-view"), identity.identity).toBeVisible({ timeout: 15_000 });
}

async function expectManifestIdentityTruth(page, identity, navigationParents) {
  const navigationParent = navigationParents[identity.view];
  expect(navigationParent, `${identity.identity}: declared navigation parent`).toBeTruthy();
  await expect(
    page.getByRole("link", { name: navigationParent, exact: true }).first(),
    `${identity.identity}: active navigation parent`,
  ).toHaveAttribute("aria-current", "page");
  if (identity.identity.startsWith("workflow-catalog--populated--")) {
    await expect(page.locator(".workflow-catalog__row"), `${identity.identity}: canonical definitions`).toHaveCount(14);
    await expect(page.locator(".workflow-catalog a[href^='/runs/']"), `${identity.identity}: definition-only catalog`).toHaveCount(0);
  }
  if (identity.identity.startsWith("workflow-catalog--empty--")) {
    await expect(page.getByRole("heading", { name: "No workflow definitions available" })).toBeVisible();
  }
  if (identity.identity.startsWith("workflow-detail--unreadable--")) {
    await expect(page.getByRole("heading", { name: "1 topology diagnostic" })).toBeVisible();
  }
  if (identity.identity.startsWith("workflow-detail--complex-loop--")) {
    await expect(page.getByRole("button", { name: "Select loop 02-campaign loops to 02-campaign" })).toBeVisible();
    await expect(page.getByText("02-campaign loops to 02-campaign — bounded generations")).toBeVisible();
    if (identity.breakpoint === "compact") {
      const inspector = await page.locator(".workflow-inspector").boundingBox();
      const graph = await page.locator(".workflow-detail__graph-panel").boundingBox();
      expect(inspector, `${identity.identity}: inspector is rendered`).not.toBeNull();
      expect(graph, `${identity.identity}: graph is rendered`).not.toBeNull();
      expect(inspector.y, `${identity.identity}: inspector precedes graph`).toBeLessThan(graph.y);
    }
  }
  if (identity.identity.startsWith("workflow-source--missing-source--")) {
    await expect(page.getByRole("heading", { name: "Source not found" })).toBeVisible();
  }
  if (identity.identity.startsWith("workflow-source--unreadable-source--")) {
    await expect(page.getByRole("heading", { name: "Source is unreadable" })).toBeVisible();
  }
  if (identity.identity === "run-map--blocked-causal--compact") {
    const inspector = await page.locator(".run-inspector").boundingBox();
    const graph = await page.locator(".run-map__graph-card").boundingBox();
    expect(inspector, `${identity.identity}: inspector is rendered`).not.toBeNull();
    expect(graph, `${identity.identity}: graph is rendered`).not.toBeNull();
    expect(inspector.y, `${identity.identity}: inspector precedes graph`).toBeLessThan(graph.y);
    const sourceOrder = await page.evaluate(() => {
      const inspectorElement = document.querySelector(".run-inspector");
      const graphElement = document.querySelector(".run-map__graph-card");
      return Boolean(inspectorElement?.compareDocumentPosition(graphElement) & Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(sourceOrder, `${identity.identity}: focus source order follows visual order`).toBe(true);
  }
  if (identity.identity.startsWith("ticket--proof-pass--")) {
    await expect(page.locator('.proof-row[data-verdict="pass"]'), `${identity.identity}: passing rows`).toHaveCount(3);
    await expect(page.locator('.proof-row[data-verdict="fail"]'), `${identity.identity}: no failing rows`).toHaveCount(0);
    await expect(page.locator(".proof-row").filter({ hasText: "Criterion 3" }), `${identity.identity}: Criterion 3 passes`).toHaveAttribute("data-verdict", "pass");
  }
  if (identity.identity.startsWith("ticket--proof-fail--")) {
    await expect(page.locator(".proof-row").filter({ hasText: "Criterion 3" }), `${identity.identity}: Criterion 3 fails`).toHaveAttribute("data-verdict", "fail");
  }
}

async function expectKeyboardParity(page, identity) {
  const selector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const result = await page.locator(selector).evaluateAll((elements) => {
    const interactive = elements.filter((element) => {
      const style = getComputedStyle(element);
      const bounds = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && bounds.width > 0 && bounds.height > 0
        && !(element as HTMLButtonElement).disabled && element.getAttribute("aria-disabled") !== "true"
        && element.getAttribute("role") !== "tablist";
    });
    const failures = [];
    for (const element of interactive) {
      const target = element as HTMLElement;
      target.focus();
      const active = document.activeElement;
      const replacement = active?.getAttribute("role") === target.getAttribute("role")
        && active?.textContent?.trim() === target.textContent?.trim();
      if (active !== target && !replacement) failures.push(`${target.tagName.toLowerCase()} ${(target.textContent ?? "").trim().slice(0, 48)}`);
    }
    return { checked: interactive.length, failures };
  });
  expect(result.checked, `${identity.identity}: keyboard affordances checked`).toBeGreaterThan(0);
  expect(result.failures, `${identity.identity}: keyboard reach must match pointer reach`).toEqual([]);
}

async function expectReducedMotion(page, identity) {
  expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches), identity.identity).toBe(true);
  const moving = await page.locator("*").evaluateAll((elements) => elements.filter((element) => {
    const style = getComputedStyle(element);
    const seconds = (value) => value.split(",").some((part) => {
      const duration = Number.parseFloat(part);
      return part.trim().endsWith("ms") ? duration > .001 : duration > .000001;
    });
    return seconds(style.animationDuration) || seconds(style.transitionDuration);
  }).map((element) => element.tagName.toLowerCase()));
  expect(moving, `${identity.identity}: reduced motion leaves active durations`).toEqual([]);
}

test("Observe run map stays interactive and stable across an ETag refresh", async ({ page }) => {
  test.skip(action !== "smoke" || experienceMode);
  const errors: string[] = [];
  const remoteRequests: string[] = [];
  const apiMethods: string[] = [];
  const apiResponses: Array<{ status: number; etag: string }> = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().startsWith("http") && !request.url().startsWith(origin)) {
      remoteRequests.push(request.url());
    }
    if (request.url().startsWith(origin)) {
      const path = new URL(request.url()).pathname;
      if (path.startsWith("/api/")) apiMethods.push(request.method());
    }
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/v1/views/run-map") {
      apiResponses.push({ status: response.status(), etag: response.headers().etag ?? "" });
    }
  });
  await page.setViewportSize({ width: 1280, height: 800 });
  const documentResponse = await page.goto(`${origin}/runs/run-gamma`);
  expect(documentResponse?.headers()["content-security-policy"]).toContain("default-src 'self'");
  expect(documentResponse?.headers()["x-content-type-options"]).toBe("nosniff");
  await expect(page.locator("main[data-mode=observe]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "run-gamma" })).toBeVisible();
  await expect(page.locator(".run-map__read-only")).toContainText("Observe only");
  await expect(page.locator(".run-map__canvas")).toBeVisible();
  await expect.poll(() => apiResponses.some(({ status, etag }) => status === 200 && Boolean(etag))).toBe(true);
  const firstEtag = apiResponses.find(({ status }) => status === 200)?.etag ?? "";
  expect(firstEtag).toMatch(/^"[0-9a-f]{64}"$/);
  await page.getByRole("button", { name: "Expand all tickets" }).click();

  const buildNode = page.locator(".react-flow__node").filter({ hasText: "G5" });
  const buildTicket = buildNode.locator(".run-ticket-node");
  await expect(buildNode).toBeVisible();
  await expect(buildTicket).toHaveAttribute("data-status", "running");
  expect(await page.locator("[draggable=true]").count()).toBe(0);
  await buildNode.focus();
  await expect(buildNode).toBeFocused();
  await buildNode.click();
  await expect(buildNode).toHaveClass(/selected/);

  const viewport = page.locator(".react-flow__viewport");
  const beforeZoom = await viewport.getAttribute("style");
  await page.locator(".react-flow__controls-zoomin").click();
  await expect.poll(() => viewport.getAttribute("style")).not.toBe(beforeZoom);
  const afterZoom = await viewport.getAttribute("style");
  await expect.poll(() => apiResponses.some(({ status }) => status === 304)).toBe(true);
  const ticketPath = join(stateRoot, "tickets", "run-gamma", "G5.md");
  const ticket = await readFile(ticketPath, "utf8");
  await writeFile(ticketPath, ticket.replace("status: claimed", "status: complete"), "utf8");
  await expect.poll(
    () => apiResponses.some(({ status, etag }) => status === 200 && Boolean(etag) && etag !== firstEtag),
    { timeout: 5_000 }
  ).toBe(true);
  await expect(buildTicket).toHaveAttribute("data-status", "complete");
  await expect(buildNode).toHaveClass(/selected/);
  expect(await viewport.getAttribute("style")).toBe(afterZoom);

  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  await page.setViewportSize({ width: 640, height: 780 });
  const rail = await page.locator(".rail").boundingBox();
  const canvas = await page.locator(".run-map__canvas").boundingBox();
  expect(rail).not.toBeNull();
  expect(canvas).not.toBeNull();
  expect(canvas.y).toBeGreaterThanOrEqual(rail.y + rail.height - 1);
  await expect(buildNode).toHaveClass(/selected/);

  expect(apiMethods.length).toBeGreaterThan(0);
  expect(apiMethods.every((method) => method === "GET")).toBe(true);
  expect(remoteRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("compiled experience preserves keyboard-reachable observer state across refresh", async ({ page }) => {
  test.skip(action !== "smoke" || !experienceMode);
  const errors: string[] = [];
  const remoteRequests: string[] = [];
  const apiStatuses: number[] = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().startsWith("http") && !request.url().startsWith(origin)) remoteRequests.push(request.url());
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/v1/views/now") apiStatuses.push(response.status());
  });

  await page.setViewportSize({ width: 1280, height: 800 });
  const response = await page.goto(`${origin}/now`);
  expect(response?.headers()["content-security-policy"]).toContain("default-src 'self'");
  await expect(page.locator("main[data-mode=observe]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Now" })).toBeVisible();

  const attention = page.getByRole("button", { name: "Needs attention", exact: true });
  await attention.click();
  await expect(attention).toHaveAttribute("aria-pressed", "true");
  const firstRunDetail = page.locator(".now-run-card__open").first();
  await expect(firstRunDetail).toHaveAttribute("href", /^\/runs\//);
  const pause = page.getByRole("button", { name: "Pause live" });
  await pause.click();
  await expect(page.getByRole("button", { name: "Resume live" })).toHaveAttribute("aria-pressed", "true");

  await firstRunDetail.focus();
  await expect(firstRunDetail).toBeFocused();
  await expect.poll(() => apiStatuses.includes(304)).toBe(true);
  await expect(attention).toHaveAttribute("aria-pressed", "true");
  await expect(firstRunDetail).toBeFocused();
  await expect(page.getByRole("button", { name: "Resume live" })).toBeVisible();

  await page.setViewportSize({ width: 640, height: 780 });
  await expect(page.locator(".now-hierarchy")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(641);
  expect(remoteRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("experience drill-down stays actionable and bounded in a real browser", async ({ page }) => {
  test.skip(action !== "smoke" || !experienceMode);
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 1024 });

  await page.goto(`${origin}/workflows`);
  const workflowCatalog = page.getByRole("list", { name: "Workflow definitions" });
  await expect(workflowCatalog.locator(":scope > li")).toHaveCount(14);
  await expect(workflowCatalog.locator("a[href^='/runs/']")).toHaveCount(0);
  await page.getByRole("link", { name: "fix", exact: true }).click();
  await expect(page).toHaveURL(/\/workflows\/fix$/);
  await expect(page.getByRole("heading", { level: 1, name: "fix" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1, name: "Workflows" })).toBeVisible();

  await page.goto(`${origin}/runs/run-gamma`);
  await page.getByRole("button", { name: "Fleet" }).click();
  await page.getByRole("link", { name: /run-delta/ }).click();
  await expect(page).toHaveURL(/\/runs\/run-delta$/);
  await expect(page.getByRole("heading", { level: 1, name: "run-delta" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1, name: "run-gamma" })).toBeVisible();

  await page.goto(`${origin}/sessions`);
  const diagnostic = page.locator(".sessions-view__diagnostic");
  await expect(diagnostic).toContainText("Metadata needs attention");
  expect((await diagnostic.textContent())?.length).toBeLessThan(180);
  await expect(diagnostic).not.toContainText("not-an-encoded-path");

  await page.goto(`${origin}/sessions/11111111-1111-4111-8111-111111111111`);
  const agent = page.locator(".react-flow__node").filter({ has: page.locator('[data-kind="agent"]') }).nth(5);
  await expect(agent).toBeVisible();
  const agentLabel = await agent.locator("strong").textContent();
  const agentBox = await agent.boundingBox();
  const canvasBox = await page.locator(".session-graph-canvas").boundingBox();
  expect(agentBox).not.toBeNull();
  expect(canvasBox).not.toBeNull();
  expect(agentBox.y).toBeGreaterThanOrEqual(canvasBox.y);
  expect(agentBox.y + agentBox.height).toBeLessThanOrEqual(canvasBox.y + canvasBox.height);
  await agent.click();
  await expect(page.locator("#session-inspector-heading")).toHaveText(agentLabel || "");

  await page.goto(`${origin}/now`);
  const nowRun = page.locator(".now-run-card").first();
  await expect(nowRun).toBeVisible();
  const objectiveHeights = await page.locator(".now-objective-summary").evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().height));
  expect(Math.max(...objectiveHeights)).toBeLessThanOrEqual(72);
  await expect(nowRun.getByText("Full objective")).toBeVisible();
  await nowRun.locator(".now-run-card__open").click();
  await expect(page).toHaveURL(/\/runs\/[^/?]+$/);
  await expect(page.locator('.run-map[data-view="run-map"]')).toBeVisible();

  await page.goto(`${origin}/friction`);
  await expect(page.locator(".friction-record")).toHaveCount(50);
  await expect(page.getByText("historical-browser-guard")).toHaveCount(0);
  await expect(page.getByText("Showing 50 of 130 records")).toBeVisible();
  await page.getByRole("button", { name: "Show 50 more friction records" }).click();
  await expect(page.locator(".friction-record")).toHaveCount(100);
  await expect(page.getByText("Showing 100 of 130 records")).toBeVisible();
});

test("capture every manifest identity", async ({ page }) => {
  test.skip(action !== "capture");
  test.setTimeout(180_000);
  const manifest = JSON.parse(await readFile(process.env.ORCHFLOWS_UI_MANIFEST, "utf8"));
  const output = process.env.ORCHFLOWS_UI_OUTPUT;
  await mkdir(output, { recursive: true });
  for (const identity of manifest.views) {
    const [width, height] = manifest.breakpoints[identity.breakpoint];
    await openManifestIdentity(page, identity, width, height);
    await expectManifestIdentityTruth(page, identity, manifest.navigationParents);
    await page.screenshot({ path: join(output, `${identity.identity}.png`), fullPage: true });
  }
});

test("audit every manifest identity", async ({ page }) => {
  test.skip(action !== "audit");
  test.setTimeout(600_000);
  const manifest = JSON.parse(await readFile(process.env.ORCHFLOWS_UI_MANIFEST, "utf8"));
  for (const identity of manifest.views) {
    const [width, height] = manifest.breakpoints[identity.breakpoint];
    await page.emulateMedia({ forcedColors: "none", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height);
    await expectManifestIdentityTruth(page, identity, manifest.navigationParents);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(result.violations, identity.identity).toEqual([]);

    await openManifestIdentity(page, identity, Math.max(320, Math.floor(width / 2)), height);
    const reflow = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(reflow.scroll, `${identity.identity}: 200% zoom-equivalent reflow`).toBeLessThanOrEqual(reflow.width + 1);

    await page.emulateMedia({ forcedColors: "active", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height);
    expect(await page.evaluate(() => matchMedia("(forced-colors: active)").matches), identity.identity).toBe(true);
    const forced = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(forced.violations, `${identity.identity}: forced colors`).toEqual([]);

    await page.emulateMedia({ forcedColors: "none", reducedMotion: "reduce" });
    await openManifestIdentity(page, identity, width, height);
    await expectReducedMotion(page, identity);

    await page.emulateMedia({ forcedColors: "none", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height);
    await expectKeyboardParity(page, identity);
  }
});
