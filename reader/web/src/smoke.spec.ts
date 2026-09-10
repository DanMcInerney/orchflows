import { openManifestIdentity, expectManifestIdentityTruth, expectKeyboardParity, expectReducedMotion } from "./manifest-contract";
import { expectLiveTicket } from "./features/inspector/browser-contract";
import { expectRunActivation, expectRunIdentity } from "./features/run-map/browser-contract";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { type ChildProcess } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import {
  requiredEnv,
  startOriginProcess,
  type NowProjection,
  type ViewManifest,
} from "./smoke_support";

const executablePath = process.env.ORCHFLOWS_BROWSER_EXECUTABLE || undefined;
test.use({ launchOptions: executablePath ? { executablePath } : undefined });

let serverProcess: ChildProcess | undefined;
let devProcess: ChildProcess | undefined;
let stateRoot = "";
let origin = "";
const action = process.env.ORCHFLOWS_UI_ACTION || "smoke";
const apiOrigin = process.env.ORCHFLOWS_UI_API_ORIGIN || "";
const experienceMode = process.env.ORCHFLOWS_UI_EXPERIENCE === "1";
const fixtureRoot = resolve("..", "tests", "fixtures");

test.beforeAll(async () => {
  if (action !== "smoke") {
    const viteScript = resolve("node_modules", "vite", "bin", "vite.js");
    const started = await startOriginProcess(
      process.execPath,
      [viteScript, "--host", "127.0.0.1", "--port", "0"],
      "vite",
      process.cwd(),
      { ...process.env, ORCHFLOWS_UI_API_ORIGIN: apiOrigin },
    );
    devProcess = started.child;
    origin = started.origin;
    return;
  }
  stateRoot = await mkdtemp(join(tmpdir(), "orchflows-smoke-"));
  await mkdir(join(stateRoot, "tickets"));
  for (const run of ["run-alpha", "run-beta", "run-delta", "run-epsilon", "run-gamma"]) {
    await cp(join(fixtureRoot, "ui", run), join(stateRoot, "tickets", run), { recursive: true });
  }
  await cp(join(fixtureRoot, "ui", "runs"), join(stateRoot, "runs"), { recursive: true });
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
  await cp(join(fixtureRoot, "transcripts"), transcriptRoot, { recursive: true });
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
  const started = await startOriginProcess(
    process.env.ORCHFLOWS_PYTHON || "python",
    ["-u", "scripts/ui.py", "--root", stateRoot, "--transcripts", transcriptRoot, "--port", "0"],
    "reader",
    process.cwd(),
    process.env,
  );
  serverProcess = started.child;
  origin = started.origin;
});

test.afterAll(async () => {
  serverProcess?.kill();
  devProcess?.kill();
  await rm(stateRoot, { recursive: true, force: true });
});

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
  await expectRunIdentity(page, origin, "run-gamma");
  await expect(page.locator(".run-map__read-only")).toContainText("Observe only");
  await page.getByRole("button", { name: "Open canonical graph" }).click();
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
  if (!rail || !canvas) throw new Error("mobile run map must render rail and canvas");
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
  test.setTimeout(150_000);
  await page.setViewportSize({ width: 1440, height: 1024 });

  await page.goto(`${origin}/workflows`);
  const workflowCatalog = page.getByRole("list", { name: "Workflow definitions" });
  const workflowIds = [
    "3d-browser-game", "bakeoff", "benchmaker", "checkpointed-build",
    "drift-canary", "evolve", "orch-build-workflow", "orch-do", "orch-judge",
    "orch-self-improve", "orchflows-videos", "recent-search", "renovate",
    "skill-tournament", "tiktok-video",
  ];
  await expect(workflowCatalog.locator(":scope > li")).toHaveCount(workflowIds.length);
  await expect.poll(async () => (await workflowCatalog.getByRole("link").allTextContents()).sort()).toEqual(workflowIds);
  await expect(workflowCatalog.locator("a[href^='/runs/']")).toHaveCount(0);
  await page.getByRole("link", { name: "evolve", exact: true }).click();
  await expect(page).toHaveURL(/\/workflows\/evolve$/);
  await expect(page.getByRole("heading", { level: 1, name: "evolve" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1, name: "Workflows" })).toBeVisible();

  await page.goto(`${origin}/runs/run-gamma`);
  await page.getByRole("button", { name: "Fleet", exact: true }).click();
  await page.locator('.run-fleet__row[href="/runs/run-delta"]').click();
  await expect(page).toHaveURL(/\/runs\/run-delta$/);
  await expectRunIdentity(page, origin, "run-delta");
  await page.goBack();
  await expectRunIdentity(page, origin, "run-gamma");

  await page.goto(`${origin}/sessions`);
  const diagnostic = page.locator(".sessions-view__diagnostic");
  await expect(diagnostic).toContainText("Metadata needs attention");
  expect((await diagnostic.textContent())?.length).toBeLessThan(180);
  await expect(diagnostic).not.toContainText("not-an-encoded-path");

  await page.goto(`${origin}/sessions/11111111-1111-4111-8111-111111111111`);
  const agent = page.getByLabel("All session agents").getByRole("button").nth(5);
  await agent.scrollIntoViewIfNeeded();
  const agentLabel = await agent.locator("strong").textContent();
  await agent.focus();
  await agent.press("Enter");
  await expect(page.locator("#session-inspector-heading")).toHaveText(agentLabel || "");
  await expect(agent).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: /Show full topology/ }).click();
  await expect(page.locator(".react-flow__node")).toHaveCount(await page.getByLabel("All session agents").getByRole("button").count());

  await page.goto(`${origin}/now`);
  const nowRun = page.locator(".now-run-card").first();
  await expect(nowRun).toBeVisible();
  const objectiveHeights = await page.locator(".now-objective-summary").evaluateAll((elements: Element[]) => elements.map((element: Element) => element.getBoundingClientRect().height));
  expect(Math.max(...objectiveHeights)).toBeLessThanOrEqual(72);
  await expect(nowRun.getByText("Full objective")).toBeVisible();

  // The served projection carries folder identity and completion timing, and
  // carries no host path, origin or workspace out of the fixture run records.
  const nowPayload = await (await page.request.get(`${origin}/api/v1/views/now`)).json() as NowProjection;
  const projected = Object.fromEntries(nowPayload.runs.map((run) => [run.id, run]));
  expect(projected["run-gamma"].repository, "live run folder leaf").toBe("atlas-web");
  expect(projected["run-delta"].repository, "backslash name reduces to the same leaf").toBe("atlas-web");
  expect(projected["run-beta"].repository, "no run.json records no folder").toBe("");
  expect(projected["run-epsilon"].terminal_at).toBe("2026-08-25T11:40:00Z");
  expect(projected["run-epsilon"].terminal_status).toBe("limited");
  expect(projected["run-gamma"].terminal_at, "a live run has no terminal timing").toBe("");
  const nowBody = JSON.stringify(nowPayload);
  for (const forbidden of ["/srv/fleet", "C:\\fleet", "example.invalid", ".worktrees"]) {
    expect(nowBody.includes(forbidden), `privacy wall holds against ${forbidden}`).toBe(false);
  }

  // Running folders lead, the trouble-bearing folder first: `aegis-notes` sorts
  // ahead of `atlas-web` alphabetically and yields to it because it needs nothing.
  const runningFolders = page.locator("section[aria-labelledby='now-running-heading'] .now-folder h3");
  await expect(runningFolders, "running folders, trouble first").toHaveText(["atlas-web", "aegis-notes", "Folder unrecorded"]);
  const pastFolders = page.locator("section[aria-labelledby='now-past-heading'] .now-folder h3");
  await expect(pastFolders, "past folders by newest completion").toHaveText(["beacon-cli", "atlas-web"]);
  const runningBand = await page.locator("section[aria-labelledby='now-running-heading']").boundingBox();
  const pastBand = await page.locator("section[aria-labelledby='now-past-heading']").boundingBox();
  if (!runningBand || !pastBand) throw new Error("Now must render running and past bands");
  expect(runningBand.y, "running work precedes finished work").toBeLessThan(pastBand.y);

  // A running card whose canonical data reads pairs the summarized flowchart
  // with what the run is doing now; one whose data does not infers no progress.
  const readableCard = page.locator(".now-folder")
    .filter({ has: page.getByRole("heading", { level: 3, name: "aegis-notes" }) })
    .locator(".now-run-card").first();
  await expect(readableCard.locator(".workflow-summary")).toBeVisible();
  await expect(readableCard.locator(".workflow-summary__node").first()).toBeVisible();
  await expect(readableCard.locator(".now-run-card__task"), "task summary beside the flow").toContainText("Working on");
  expect(await page.locator(".now-run-card .workflow-summary").count(), "a summary flow per readable card").toBeGreaterThan(1);
  const runningCard = page.locator("section[aria-labelledby='now-running-heading'] .now-run-card").first();
  await expect(runningCard.locator(".now-unknown"), "unreadable tickets infer no flow").toBeVisible();
  await expect(runningCard.locator(".workflow-summary")).toHaveCount(0);

  // A finished card states its recorded outcome and finish time instead.
  const finishedCard = page.locator("section[aria-labelledby='now-past-heading'] .now-run-card").first();
  await expect(finishedCard.locator(".now-run-card__task")).toContainText("limited");
  await expect(finishedCard.locator(".now-run-card__task")).toContainText("2026-08-25T11:40:00Z");

  await runningCard.locator(".now-run-card__open").click();
  await expect(page).toHaveURL(/\/runs\/run-gamma$/);
  await expect(page.locator('.run-map[data-view="run-map"]')).toBeVisible();

  // From a skill in the sequence to the ticket that skill is running.
  const skillNode = page.locator(".run-skills__node").first();
  await expect(skillNode).toBeVisible();
  const skillTicket = (await skillNode.locator(".run-skills__ticket").textContent())?.trim();
  if (!skillTicket) throw new Error("skill sequence must identify its active ticket");
  expect(skillTicket).toMatch(/^G\d$/);
  await expect(skillNode).toHaveAttribute("href", `/runs/run-gamma/tickets/${skillTicket}`);
  await skillNode.click();
  await expect(page).toHaveURL(new RegExp(`/runs/run-gamma/tickets/${skillTicket}$`));
  await expect(page.locator('.run-map[data-view="run-map"]'), "the run map yields to the ticket route").toHaveCount(0);

  // The ticket detail the drill-down lands on, asserted at the live URL the
  // click above already reached — no `?fixture=`, so the reader's own payload
  // renders it.
  await expect(page.locator(".ticket-inspector"), "the live ticket detail renders").toBeVisible();
  const ticketResponse = await (await page.request.get(`${origin}/api/v1/views/inspector?run=run-gamma&ticket=${skillTicket}`)).json();
  await expect(page.getByRole("heading", { level: 1, name: ticketResponse.ticket.title || skillTicket })).toBeVisible();

  await page.goBack();
  await expect(page.locator('.run-map[data-view="run-map"]')).toBeVisible();

  await page.goto(`${origin}/friction`);
  await expect(page.locator(".friction-record")).toHaveCount(50);
  await expect(page.getByText("historical-browser-guard")).toHaveCount(0);
  await expect(page.getByText("Showing 50 of 130 records")).toBeVisible();
  await page.getByRole("button", { name: "Show 50 more friction records" }).click();
  await expect(page.locator(".friction-record")).toHaveCount(100);
  await expect(page.getByText("Showing 100 of 130 records")).toBeVisible();
});

for (const [breakpoint, width, height] of [["wide", 1440, 1024], ["compact", 1024, 768]] as const) {
  test(`live ticket contract ${breakpoint}`, async ({ page }, testInfo) => {
    test.skip(!experienceMode || !["smoke", "contract"].includes(action));
    await page.setViewportSize({ width, height });
    await expectLiveTicket(page, origin);
    await page.screenshot({ path: testInfo.outputPath("ticket-overview.png"), fullPage: true });
  });
  test(`run graph activation ${breakpoint}`, async ({ page }, testInfo) => {
    test.skip(!experienceMode || !["smoke", "contract"].includes(action));
    await page.setViewportSize({ width, height });
    await expectRunActivation(page, origin);
    await page.locator('.react-flow__node[data-id="G2"]').press("Enter");
    await page.screenshot({ path: testInfo.outputPath("run-keyboard-selection.png"), fullPage: true });
  });
}

test("capture every manifest identity", async ({ page }) => {
  test.skip(action !== "capture");
  test.setTimeout(180_000);
  const manifest = JSON.parse(await readFile(requiredEnv("ORCHFLOWS_UI_MANIFEST"), "utf8")) as ViewManifest;
  const output = requiredEnv("ORCHFLOWS_UI_OUTPUT");
  await mkdir(output, { recursive: true });
  for (const identity of manifest.views) {
    const [width, height] = manifest.breakpoints[identity.breakpoint];
    await openManifestIdentity(page, identity, width, height, origin);
    await expectManifestIdentityTruth(page, identity, manifest.navigationParents);
    await page.screenshot({ path: join(output, `${identity.identity}.png`), fullPage: true });
  }
});

test("audit every manifest identity", async ({ page }) => {
  test.skip(action !== "audit");
  test.setTimeout(600_000);
  const manifest = JSON.parse(await readFile(requiredEnv("ORCHFLOWS_UI_MANIFEST"), "utf8")) as ViewManifest;
  for (const identity of manifest.views) {
    const [width, height] = manifest.breakpoints[identity.breakpoint];
    await page.emulateMedia({ forcedColors: "none", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height, origin);
    await expectManifestIdentityTruth(page, identity, manifest.navigationParents);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(result.violations, identity.identity).toEqual([]);

    await openManifestIdentity(page, identity, Math.max(320, Math.floor(width / 2)), height, origin);
    const reflow = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(reflow.scroll, `${identity.identity}: 200% zoom-equivalent reflow`).toBeLessThanOrEqual(reflow.width + 1);

    await page.emulateMedia({ forcedColors: "active", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height, origin);
    expect(await page.evaluate(() => matchMedia("(forced-colors: active)").matches), identity.identity).toBe(true);
    const forced = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(forced.violations, `${identity.identity}: forced colors`).toEqual([]);

    await page.emulateMedia({ forcedColors: "none", reducedMotion: "reduce" });
    await openManifestIdentity(page, identity, width, height, origin);
    await expectReducedMotion(page, identity);

    await page.emulateMedia({ forcedColors: "none", reducedMotion: "no-preference" });
    await openManifestIdentity(page, identity, width, height, origin);
    await expectKeyboardParity(page, identity);
  }
});
