// @ts-nocheck -- Playwright owns this Node-side harness; application code remains strict.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const dist = resolve(process.cwd(), "web", "dist");
const executablePath = process.env.ORCHFLOWS_BROWSER_EXECUTABLE || undefined;
test.use({ launchOptions: executablePath ? { executablePath } : undefined });

let server;
let origin = "";
let taggedReads = 0;
const serverEvents: string[] = [];

function send(response, status, body, headers = {}) {
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Length": Buffer.byteLength(body),
    ...headers
  });
  response.end(body);
}

test.beforeAll(async () => {
  const index = await readFile(resolve(dist, "index.html"));
  server = createServer(async (request, response) => {
    const url = new URL(request.url || "/", "http://127.0.0.1");
    if (url.pathname === "/api/observe") {
      const tag = request.headers["if-none-match"];
      serverEvents.push(`api:${tag || "none"}:${url.searchParams.toString()}`);
      if (tag === '"one"' && taggedReads++ === 0) {
        send(response, 304, "", { ETag: '"one"' });
        return;
      }
      const changed = tag === '"one"' || tag === '"two"';
      const snapshot = {
        revision: changed ? "two" : "one",
        active: true,
        nodes: [
          { id: "A", label: "Acquire", status: "complete" },
          { id: "B", label: "Build", status: changed ? "complete" : "claimed" }
        ],
        edges: [{ id: "A-B", source: "A", target: "B" }]
      };
      const body = JSON.stringify(snapshot);
      setTimeout(() => send(response, 200, body, {
        "Content-Type": "application/json",
        ETag: changed ? '"two"' : '"one"'
      }), 80);
      return;
    }
    if (/^\/assets\/[A-Za-z0-9._-]+$/.test(url.pathname)) {
      serverEvents.push(`asset:${url.pathname}`);
      const body = await readFile(resolve(dist, url.pathname.slice(1)));
      const type = url.pathname.endsWith(".css") ? "text/css" : "text/javascript";
      send(response, 200, body, { "Content-Type": type });
      return;
    }
    send(response, 200, index, { "Content-Type": "text/html; charset=utf-8" });
  });
  await new Promise((resolveListen) => server.listen(0, "127.0.0.1", resolveListen));
  const address = server.address();
  origin = `http://127.0.0.1:${address.port}`;
});

test.afterAll(async () => {
  await new Promise((resolveClose) => server.close(resolveClose));
});

test("Observe platform stays interactive and stable across a reader refresh", async ({ page }) => {
  const errors: string[] = [];
  const remoteRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.url().startsWith("http") && !request.url().startsWith(origin)) {
      remoteRequests.push(request.url());
    }
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
  await page.goto(`${origin}/ticket?run=run-alpha&id=B`);
  await expect(page.locator("main[data-mode=observe]")).toBeVisible();
  await expect(page.getByText("revision one")).toBeVisible();
  await expect(page.locator(".canvas")).toHaveAttribute("data-editing", "disabled");
  expect(await page.locator("[draggable=true], .react-flow__handle").count()).toBe(0);
  expect(serverEvents.some((event) => event.includes("run=run-alpha") && event.includes("id=B"))).toBe(true);

  await expect.poll(
    () => serverEvents.some((event) => event.startsWith("asset:/assets/layout.worker-"))
  ).toBe(true);
  await expect.poll(
    () => serverEvents.some((event) => event.startsWith("asset:/assets/elk.worker-"))
  ).toBe(true);
  await expect.poll(() => page.evaluate(() => window.__orchflowsWorkerErrors)).toEqual([]);
  await expect.poll(
    () => page.evaluate(() => window.__orchflowsWorkerMessages.length),
    { timeout: 10_000 }
  ).toBeGreaterThan(0);

  const buildNode = page.locator(".react-flow__node").filter({ hasText: "Build" });
  await expect(buildNode).toBeVisible();
  await buildNode.focus();
  await page.keyboard.press("Enter");
  await expect(buildNode).toHaveClass(/selected/);

  const viewport = page.locator(".react-flow__viewport");
  const beforeZoom = await viewport.getAttribute("style");
  await page.locator(".react-flow__controls-zoomin").click();
  await expect.poll(() => viewport.getAttribute("style")).not.toBe(beforeZoom);
  const afterZoom = await viewport.getAttribute("style");
  await expect(page.getByText("revision two")).toBeVisible({ timeout: 5_000 });
  await expect(buildNode).toHaveClass(/selected/);
  expect(await viewport.getAttribute("style")).toBe(afterZoom);

  await expect.poll(
    () => serverEvents.some((event) => event.startsWith("asset:/assets/layout.worker-"))
  ).toBe(true);
  const firstApi = serverEvents.findIndex((event) => event.startsWith("api:"));
  const workerAsset = serverEvents.findIndex((event) => event.startsWith("asset:/assets/layout.worker-"));
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
