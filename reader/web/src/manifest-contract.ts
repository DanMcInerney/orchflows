import { expect, type Page } from "@playwright/test";
import type { ViewIdentity } from "./smoke_support";

export async function openManifestIdentity(page: Page, identity: ViewIdentity, width: number, height: number, origin: string) {
  await page.setViewportSize({ width, height });
  await page.goto(`${origin}${identity.path}`);
  await expect(page.locator(".foundation-view"), identity.identity).toBeVisible({ timeout: 45_000 });
}

export async function expectManifestIdentityTruth(
  page: Page,
  identity: ViewIdentity,
  navigationParents: Record<string, string>,
) {
  const navigationParent = navigationParents[identity.view];
  expect(navigationParent, `${identity.identity}: declared navigation parent`).toBeTruthy();
  await expect(
    page.getByRole("link", { name: navigationParent, exact: true }).first(),
    `${identity.identity}: active navigation parent`,
  ).toHaveAttribute("aria-current", "page");
  if (identity.identity.startsWith("workflow-catalog--populated--")) {
    await expect(page.locator(".workflow-catalog__row"), `${identity.identity}: canonical definitions`).toHaveCount(13);
    await expect(page.locator(".workflow-catalog a[href^='/runs/']"), `${identity.identity}: definition-only catalog`).toHaveCount(0);
  }
  if (identity.identity.startsWith("workflow-catalog--empty--")) {
    await expect(page.getByRole("heading", { name: "No workflow definitions available" })).toBeVisible();
  }
  if (identity.identity.startsWith("workflow-detail--unreadable--")) {
    await expect(page.getByRole("heading", { name: "1 topology diagnostic" })).toBeVisible();
  }
  if (identity.identity.startsWith("workflow-detail--complex-loop--")) {
    await expect(page.getByRole("heading", { name: "Overview", exact: true })).toBeVisible();
    await page.getByText("Full topology, ticket templates and sources", { exact: true }).click();
    await page.getByText("Text equivalent and all source links", { exact: true }).click();
    await expect(page.getByRole("button", { name: "Select loop relation: 02-campaign loops to 02-campaign" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Skills called, step by step" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Select Definition-time ticket template 02-campaign" })).toBeVisible();
    await expect(page.getByText("02-campaign loops to 02-campaign — Write candidates; verify eligibility; score blind; select by the frozen rule; repeat {{bound}}")).toBeVisible();
    await expect(page.locator(".workflow-detail__hero dd")).toHaveText(["8", "8"]);
    const verifyOccurrences = page.getByRole("button", { name: "Select Called skill orch-verify" });
    await expect(verifyOccurrences).toHaveCount(2);
    await verifyOccurrences.nth(1).click();
    await expect(verifyOccurrences.nth(0)).toHaveAttribute("aria-pressed", "false");
    await expect(verifyOccurrences.nth(1)).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Select Composition definition evolve" }).click();
    await page.locator(".workflow-graph").evaluate((element) => { element.scrollLeft = 0; });
    const inspector = await page.locator(".workflow-inspector").boundingBox();
    if (!inspector) throw new Error(`${identity.identity}: selected details must render`);
    expect(inspector.y).toBeGreaterThanOrEqual(0);
    expect(inspector.y).toBeLessThan((page.viewportSize()?.height ?? 0));
    await page.getByRole("button", { name: "Close selected details", exact: true }).click();
    await page.getByText("Text equivalent and all source links", { exact: true }).click();
    await page.getByText("Full topology, ticket templates and sources", { exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));

  }
  if (identity.identity.startsWith("workflow-detail--callable--")) {
    await page.getByText("Source references and definition details", { exact: true }).click();
    await expect(page.getByRole("heading", { name: "Referenced skills and scripts" })).toBeVisible();
    await expect(page.locator(".workflow-detail__hero dd")).toHaveText(["6", "5"]);
    await expect(page.locator("[data-call-source='workflow:orch-spec']")).toHaveCount(5);
    await expect(page.locator("[data-call-target='skill:orch-frontier'], [data-call-target='skill:orch-integrate']")).toHaveCount(2);
    await page.getByText("Source references and definition details", { exact: true }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
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
    if (!inspector || !graph) throw new Error(`${identity.identity}: graph and inspector must render`);
    expect(inspector.y, `${identity.identity}: inspector precedes graph`).toBeLessThan(graph.y);
    const sourceOrder = await page.evaluate(() => {
      const inspectorElement = document.querySelector(".run-inspector");
      const graphElement = document.querySelector(".run-map__graph-card");
      return Boolean(inspectorElement && graphElement
        && inspectorElement.compareDocumentPosition(graphElement) & Node.DOCUMENT_POSITION_FOLLOWING);
    });
    expect(sourceOrder, `${identity.identity}: focus source order follows visual order`).toBe(true);
  }
  if (identity.identity.startsWith("ticket--report-recorded--")) {
    await expect(page.locator(".report-body"), `${identity.identity}: report shown as recorded`).toContainText("Gate replayed at the tip");
    await expect(page.locator(".report-section"), `${identity.identity}: no historical section rows`).toHaveCount(0);
  }
  if (identity.identity.startsWith("ticket--report-historical--")) {
    await expect(page.locator(".report-era"), `${identity.identity}: earlier-grammar note`).toContainText("earlier five-section grammar");
    await expect(page.locator(".report-section h3"), `${identity.identity}: recorded section names`).toHaveText(["Result", "Verification", "Feedback", "Risks"]);
  }
}

export async function expectKeyboardParity(page: Page, identity: ViewIdentity) {
  const selector = 'summary, a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const result = await page.locator(selector).evaluateAll((elements: Element[]) => {
    const interactive = elements.filter((element: Element) => {
      for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
        if (ancestor instanceof HTMLDetailsElement && !ancestor.open) {
          const summary = ancestor.querySelector(":scope > summary");
          if (!summary?.contains(element)) return false;
        }
      }
      const style = getComputedStyle(element);
      const bounds = element.getBoundingClientRect();
      return style.visibility !== "hidden" && style.display !== "none" && bounds.width > 0 && bounds.height > 0
        && !(element as HTMLButtonElement).disabled && element.getAttribute("aria-disabled") !== "true"
        && element.getAttribute("role") !== "tablist";
    });
    const failures: string[] = [];
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

export async function expectReducedMotion(page: Page, identity: ViewIdentity) {
  expect(await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches), identity.identity).toBe(true);
  const moving = await page.locator("*").evaluateAll((elements: Element[]) => elements.filter((element: Element) => {
    const style = getComputedStyle(element);
    const seconds = (value: string) => value.split(",").some((part: string) => {
      const duration = Number.parseFloat(part);
      return part.trim().endsWith("ms") ? duration > .001 : duration > .000001;
    });
    return seconds(style.animationDuration) || seconds(style.transitionDuration);
  }).map((element) => element.tagName.toLowerCase()));
  expect(moving, `${identity.identity}: reduced motion leaves active durations`).toEqual([]);
}
