/**
 * E2E: Create reminder via UI → appears in list
 */

import { expect, test } from "@playwright/test";
import { registerAndLogin } from "./fixtures";

test("create reminder via form appears in reminders list", async ({ page }) => {
  await registerAndLogin(page);

  // Navigate to Reminders section
  await page.click("text=REMINDERS");

  // Open create dialog
  const createButton = page.locator("button", { hasText: /tạo|thêm|new|mới/i }).first();
  await createButton.click();

  // Fill in the reminder form
  const titleInput = page
    .locator('input[placeholder*="tiêu đề"], input[name="title"], input[type="text"]')
    .first();
  await titleInput.fill("Uống thuốc buổi sáng");

  // Set datetime — use a future date
  const tomorrow = new Date(Date.now() + 86400_000);
  const isoLocal = tomorrow.toISOString().slice(0, 16); // "YYYY-MM-DDTHH:MM"
  const dateInput = page.locator('input[type="datetime-local"]').first();
  if (await dateInput.isVisible()) {
    await dateInput.fill(isoLocal);
  }

  // Submit
  await page
    .locator('button[type="submit"], button:has-text("Tạo"), button:has-text("Lưu")')
    .last()
    .click();

  // Reminder should appear in the list
  await expect(page.locator("text=Uống thuốc buổi sáng")).toBeVisible({ timeout: 8_000 });
});
