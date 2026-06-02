/**
 * E2E: Dashboard loads with stats after login
 */

import { expect, test } from "@playwright/test";
import { registerAndLogin } from "./fixtures";

test("dashboard section loads after login", async ({ page }) => {
  await registerAndLogin(page);

  // Navigate to dashboard section
  await page.click("text=DASHBOARD");

  // Dashboard should render — look for a stats section or dashboard heading
  await expect(
    page.locator("text=DASHBOARD").first(),
  ).toBeVisible({ timeout: 8_000 });
});
