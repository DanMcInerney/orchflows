import { expect, type Page } from "@playwright/test";

/** Exercises application selection through React Flow's real DOM, not a graph mock. */
export async function expectRunActivation(page: Page, origin: string) {
  await page.goto(`${origin}/runs/run-gamma?fixture=full-expanded`);
  const node = page.locator('.react-flow__node[data-id="G2"]');
  await expect(node).toBeVisible();
  for (const activation of ["Enter", "Space", "pointer"] as const) {
    if (activation === "pointer") await node.click();
    else {
      await node.focus();
      await node.press(activation);
    }
    await expect(page.locator("#inspector-heading")).toHaveText("G2");
    await expect(page.getByRole("link", { name: "Open ticket G2", exact: true })).toBeVisible();
    await expect(node).toHaveClass(/selected/);
    await expect(node).toHaveAttribute("aria-pressed", "true");
    await expect(node).toBeFocused();
    // Repeated activation is idempotent; closing returns focus to its opener.
    await node.press("Enter");
    await expect(page.locator("#inspector-heading")).toHaveText("G2");
    await page.getByRole("button", { name: "Close inspector" }).click();
    await expect(page.locator(".run-inspector")).toHaveCount(0);
    await expect(node).toBeFocused();
  }
}
