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
  const transcriptRoot = join(stateRoot, "transcripts");
  await mkdir(transcriptRoot);
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

test("Observe platform stays interactive and stable across a reader refresh", async ({ page }) => {
  test.skip(action !== "smoke" || experienceMode);
  const errors: string[] = [];
  const remoteRequests: string[] = [];
  const localRequests: string[] = [];
  const apiStatuses: number[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().startsWith("http") && !request.url().startsWith(origin)) {
      remoteRequests.push(request.url());
    }
    if (request.url().startsWith(origin)) localRequests.push(new URL(request.url()).pathname);
  });
  page.on("response", (response) => {
    if (new URL(response.url()).pathname === "/api/observe") apiStatuses.push(response.status());
  });
  await page.addInitScript(() => {
    window.__orchflowsWorkerErrors = [];
    window.__orchflowsWorkerMessages = [];
    const BrowserWorker = window.Worker;
    window.Worker = class extends BrowserWorker {
      constructor(...arguments_) {
        super(...arguments_);
        this.addEventListener("error", (event) => {
          window.__orchflowsWorkerErrors.push(event.message || "worker error");
        });
        this.addEventListener("message", (event) => {
          window.__orchflowsWorkerMessages.push(event.data);
        });
      }
    };
  });

  await page.setViewportSize({ width: 1280, height: 800 });
  const documentResponse = await page.goto(`${origin}/observe?run=run-gamma`);
  expect(documentResponse?.headers()["content-security-policy"]).toContain("default-src 'self'");
  expect(documentResponse?.headers()["x-content-type-options"]).toBe("nosniff");
  await expect(page.locator("main[data-mode=observe]")).toBeVisible();
  await expect(page.getByText(/revision [0-9a-f]{64}/)).toBeVisible();
  const firstRevision = await page.getByText(/revision [0-9a-f]{64}/).textContent();
  await expect(page.locator(".canvas")).toHaveAttribute("data-editing", "disabled");

  await expect.poll(
    () => localRequests.some((path) => path.startsWith("/assets/layout.worker-"))
  ).toBe(true);
  await expect.poll(
    () => localRequests.some((path) => path.startsWith("/assets/elk.worker-"))
  ).toBe(true);
  await expect.poll(() => page.evaluate(() => window.__orchflowsWorkerErrors)).toEqual([]);
  await expect.poll(
    () => page.evaluate(() => window.__orchflowsWorkerMessages.length),
    { timeout: 10_000 }
  ).toBeGreaterThan(0);

  const buildNode = page.locator(".react-flow__node").filter({ hasText: "G5" });
  await expect(buildNode).toBeVisible();
  expect(await page.locator("[draggable=true], .react-flow__handle").count()).toBe(0);
  await buildNode.focus();
  await page.keyboard.press("Enter");
  await expect(buildNode).toHaveClass(/selected/);

  const viewport = page.locator(".react-flow__viewport");
  const beforeZoom = await viewport.getAttribute("style");
  await page.locator(".react-flow__controls-zoomin").click();
  await expect.poll(() => viewport.getAttribute("style")).not.toBe(beforeZoom);
  const afterZoom = await viewport.getAttribute("style");
  await expect.poll(() => apiStatuses.includes(304)).toBe(true);
  const ticketPath = join(stateRoot, "tickets", "run-gamma", "G5.md");
  const ticket = await readFile(ticketPath, "utf8");
  await writeFile(ticketPath, ticket.replace("status: claimed", "status: complete"), "utf8");
  await expect.poll(async () => page.getByText(/revision [0-9a-f]{64}/).textContent(), { timeout: 5_000 }).not.toBe(firstRevision);
  await expect(buildNode).toHaveClass(/selected/);
  expect(await viewport.getAttribute("style")).toBe(afterZoom);

  await expect.poll(
    () => localRequests.some((path) => path.startsWith("/assets/layout.worker-"))
  ).toBe(true);
  const firstApi = localRequests.findIndex((path) => path === "/api/observe");
  const workerAsset = localRequests.findIndex((path) => path.startsWith("/assets/layout.worker-"));
  expect(workerAsset).toBeGreaterThan(firstApi);

  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  await page.setViewportSize({ width: 640, height: 780 });
  const rail = await page.locator(".rail").boundingBox();
  const canvas = await page.locator(".canvas").boundingBox();
  expect(rail).not.toBeNull();
  expect(canvas).not.toBeNull();
  expect(canvas.y).toBeGreaterThanOrEqual(rail.y + rail.height - 1);
  await expect(buildNode).toHaveClass(/selected/);

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
    if (new URL(response.url()).pathname === "/api/v1/experience") apiStatuses.push(response.status());
  });

  await page.setViewportSize({ width: 1280, height: 800 });
  const response = await page.goto(`${origin}/now`);
  expect(response?.headers()["content-security-policy"]).toContain("default-src 'self'");
  await expect(page.locator("main[data-mode=observe]")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Now" })).toBeVisible();

  const attention = page.getByRole("button", { name: "Needs attention", exact: true });
  await attention.click();
  await expect(attention).toHaveAttribute("aria-pressed", "true");
  const firstGroup = page.locator(".now-groups button").first();
  await firstGroup.click();
  await expect(firstGroup).toHaveAttribute("aria-expanded", "true");
  const pause = page.getByRole("button", { name: "Pause live" });
  await pause.click();
  await expect(page.getByRole("button", { name: "Resume live" })).toHaveAttribute("aria-pressed", "true");

  const summary = page.getByRole("tab", { name: "summary" });
  await summary.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "tickets" })).toHaveAttribute("aria-selected", "true");
  await expect.poll(() => apiStatuses.includes(304)).toBe(true);
  await expect(attention).toHaveAttribute("aria-pressed", "true");
  await expect(firstGroup).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("button", { name: "Resume live" })).toBeVisible();

  await page.setViewportSize({ width: 640, height: 780 });
  await expect(page.locator(".now-layout")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(641);
  expect(remoteRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("capture every manifest identity", async ({ page }) => {
  test.skip(action !== "capture");
  test.setTimeout(180_000);
  const manifest = JSON.parse(await readFile(process.env.ORCHFLOWS_UI_MANIFEST, "utf8"));
  const output = process.env.ORCHFLOWS_UI_OUTPUT;
  await mkdir(output, { recursive: true });
  for (const identity of manifest.views) {
    const [width, height] = manifest.breakpoints[identity.breakpoint];
    await page.setViewportSize({ width, height });
    await page.goto(`${origin}${identity.path}`);
    await expect(page.locator(".foundation-view")).toBeVisible();
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
