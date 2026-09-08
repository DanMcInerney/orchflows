import { expect, type Page } from "@playwright/test";

/** A real projection crosses request, validation, rendering, and tab navigation. */
export async function expectLiveTicket(page: Page, origin: string) {
  await page.goto(`${origin}/now`);
  await page.locator('.now-run-card__open[href="/runs/run-gamma"]').click();
  await page.locator('.run-skills__node[href="/runs/run-gamma/tickets/G1"]').click();
  const response = await page.request.get(`${origin}/api/v1/views/inspector?run=run-gamma&ticket=G1`);
  expect(response.status()).toBe(200);
  const payload = await response.json();
  expect(payload.ticket).toHaveProperty("standard");
  expect(payload.ticket).not.toHaveProperty("pack");
  await expect(page.getByRole("heading", { level: 1, name: "G1" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Goal", exact: true })).toBeVisible();
  await expect(page.locator(".inspector-card--objective")).toContainText(payload.ticket.sections.goal);
  const details = page.getByRole("tab", { name: "Details", exact: true });
  await details.click();
  await expect(details).toHaveAttribute("aria-selected", "true");
  await expect(page.getByText("Standard", { exact: true })).toBeVisible();
  await details.press("ArrowRight");
  await expect(page.getByRole("tab", { name: /^Report/ })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Raw", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Raw ticket markdown" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("tab", { name: /^Report/ })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Overview", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Goal", exact: true })).toBeVisible();
}
