import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { type ChildProcess } from "node:child_process";
import { cp, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { requiredEnv, startOriginProcess } from "../../smoke_support";
import { schema } from "./data/schema";

// Run against the served distribution, never Vite. --output selects durable evidence.
let server: ChildProcess | undefined;
let stateRoot = "";
let origin = "";
const sessionId = "11111111-1111-4111-8111-111111111111";
const executablePath = process.env.ORCHFLOWS_BROWSER_EXECUTABLE || undefined;
test.use({ screenshot: "only-on-failure", launchOptions: executablePath ? { executablePath } : undefined });
test.setTimeout(60000);

test.beforeAll(async () => {
  stateRoot = await mkdtemp(join(tmpdir(), "orchflows-session-graph-"));
  await mkdir(join(stateRoot, "tickets"));
  await cp(resolve("..", "tests", "fixtures", "transcripts"), join(stateRoot, "transcripts"), { recursive: true });
  const started = await startOriginProcess(
    requiredEnv("ORCHFLOWS_PYTHON"),
    ["-u", "scripts/ui.py", "--root", stateRoot, "--transcripts", join(stateRoot, "transcripts"), "--port", "0"],
    "reader", process.cwd(), process.env,
  );
  server = started.child;
  origin = started.origin;
});

test.afterAll(async () => {
  if (server && server.exitCode === null) {
    const stopped = new Promise<void>((resolveExit) => server!.once("exit", () => resolveExit()));
    server.kill();
    await stopped;
  }
  if (stateRoot) await rm(stateRoot, { recursive: true, force: true });
});

for (const [breakpoint, width, height] of [["wide", 1440, 1024], ["compact", 1024, 768]] as const) {
  for (const count of [4, 25]) {
    test(`compiled ${count}-node session preserves visible keyboard selection at ${breakpoint}`, async ({ page, request }, info) => {
      await page.setViewportSize({ width, height });
      const response = await request.get(`${origin}/api/v1/views/session-graph?session=${sessionId}`);
      expect(response.ok()).toBe(true);
      const payload = schema(await response.json());
      const session = payload.session!;
      expect(session.agents).toHaveLength(3);
      if (count === 25) {
        session.agents.push(...Array.from({ length: 21 }, (_, index) => ({
          ...session.agents[0], id: `stress-agent-${index}`,
        })));
        for (let index = 3; index < session.agents.length; index += 3) {
          session.agents[index].parent = session.agents[index - 1].id;
          session.agents[index].depth = 2;
        }
        session.agent_count = session.agents.length;
      }
      const statuses: number[] = [];
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
      page.on("response", (item) => {
        if (item.url().includes("/api/v1/views/session-graph?")) statuses.push(item.status());
      });
      let revision = 1;
      await page.route("**/api/v1/views/session-graph?*", (route) => {
        const etag = `"graph-lifecycle-${revision}"`;
        return route.request().headers()["if-none-match"] === etag
          ? route.fulfill({ status: 304, headers: { etag } })
          : route.fulfill({ json: payload, headers: { etag } });
      });
      await page.goto(`${origin}/sessions/${sessionId}`);
      const list = page.getByLabel("All session agents").getByRole("button");
      await expect(list).toHaveCount(count);
      await page.getByRole("button", { name: /Show full topology/ }).click();
      const nodes = page.locator(".react-flow__node");
      await expect(nodes).toHaveCount(count);
      await expect.poll(() => statuses.filter((status) => status === 304).length, { timeout: 15000 }).toBeGreaterThanOrEqual(3);
      for (const node of await nodes.all()) await expect(node).toBeVisible();
      // Record transient loss too: a fast ResizeObserver must not mask a focus-breaking hide.
      await page.evaluate(() => {
        const hidden: string[] = [];
        const graph = document.querySelector(".react-flow__nodes")!;
        graph.setAttribute("data-hidden-transitions", "[]");
        new MutationObserver((records) => {
          for (const record of records) {
            const node = record.target as HTMLElement;
            if (node.matches(".react-flow__node") &&
              (node.style.visibility === "hidden" || record.oldValue?.includes("visibility: hidden"))) {
              hidden.push(node.dataset.id!);
            }
          }
          graph.setAttribute("data-hidden-transitions", JSON.stringify(hidden));
        }).observe(graph, { subtree: true, attributes: true, attributeFilter: ["style"], attributeOldValue: true });
      });
      const identities = ["session-root", ...session.agents.map((agent) => agent.id)];
      for (const [index, id] of identities.entries()) {
        const node = page.locator(`.react-flow__node[data-id="${id}"]`);
        await expect(node).toBeVisible();
        await node.focus();
        await expect(node).toBeFocused();
        await page.keyboard.press(index % 2 ? "Space" : "Enter");
        await expect(page.locator("#session-inspector-heading")).toHaveText(id === "session-root" ? "Orchestrator" : id);
        await expect(node).toHaveClass(/selected/);
        await page.evaluate(() => new Promise<void>((done) => requestAnimationFrame(() => requestAnimationFrame(() => done()))));
        await expect(node).toBeFocused();
        await expect(page.locator(".react-flow__nodes")).toHaveAttribute("data-hidden-transitions", "[]");
      }
      await page.screenshot({ path: info.outputPath("keyboard-selection.png"), fullPage: true });
      // A new 200 must reconcile metadata without discarding measurements or selection.
      session.modified = "changed-metadata";
      revision += 1;
      await expect.poll(() => statuses.filter((status) => status === 200).length).toBe(2);
      await expect(nodes.last()).toBeFocused();
      await expect(page.locator("#session-inspector-heading")).toHaveText(identities.at(-1)!);
      await list.first().click();
      await expect(list.first()).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator("#session-inspector-heading")).toHaveText("Orchestrator");
      await expect(page.locator(".react-flow__nodes")).toHaveAttribute("data-hidden-transitions", "[]");
      const accessibility = await new AxeBuilder({ page }).include(".session-graph-view")
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      expect(accessibility.violations).toEqual([]);
      expect(errors).toEqual([]);
      await page.screenshot({ path: info.outputPath("selected-topology.png"), fullPage: true });
      await writeFile(info.outputPath("observations.json"), JSON.stringify({
        count, breakpoint, viewport: { width, height }, statuses, identities, errors,
        hiddenTransitions: [], accessibilityViolations: accessibility.violations,
      }, null, 2));
    });
  }
}
