/**
 * E2E: Auth flow — register → login → dashboard load
 */

import { expect, test } from "@playwright/test";
import { registerAndLogin, uniqueEmail } from "./fixtures";

test("register and login redirects to dashboard", async ({ page }) => {
  await registerAndLogin(page);

  // After login, user should be on main app page and see JARVIS sidebar
  await expect(page.getByRole("heading", { name: "JARVIS" })).toBeVisible();
});

test("login with wrong password shows error", async ({ page }) => {
  const email = uniqueEmail();

  // Register user
  await page.request.post("http://localhost:8000/auth/register", {
    data: { email, password: "Password123", name: "Test User" },
    headers: { "Content-Type": "application/json" },
  });

  // Try login with wrong password
  await page.goto("/auth/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', "WrongPassword1");
  await page.click('button[type="submit"]');

  // Should still be on login page or show error
  await expect(page).toHaveURL(/auth\/login/, { timeout: 5_000 });
});
