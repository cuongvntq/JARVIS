/**
 * E2E test helpers — create test users and authenticate via login UI.
 */

import { type Page, expect } from "@playwright/test";

const API_URL = "http://localhost:8000";

let _userCounter = 0;

export function uniqueEmail(): string {
  _userCounter++;
  return `e2e_${Date.now()}_${_userCounter}@test.local`;
}

export async function registerAndLogin(
  page: Page,
  opts: { email?: string; password?: string; name?: string } = {},
): Promise<{ email: string; password: string }> {
  const email = opts.email ?? uniqueEmail();
  const password = opts.password ?? "Password123";
  const name = opts.name ?? "E2E User";

  // Register via API directly
  const res = await page.request.post(`${API_URL}/auth/register`, {
    data: { email, password, name },
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok()) {
    throw new Error(`Register failed: ${res.status()} ${await res.text()}`);
  }

  // Login via UI to populate cookies + app auth state
  await page.goto("/auth/login");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');

  // Wait for redirect to main app
  await expect(page).toHaveURL("/", { timeout: 10_000 });

  return { email, password };
}
