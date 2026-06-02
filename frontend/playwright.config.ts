import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const repoRoot = path.resolve(__dirname, "..");

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",

  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      command: "uvicorn app.main:app --port 8000",
      port: 8000,
      cwd: path.join(repoRoot, "backend"),
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        APP_ENV: "test",
        DATABASE_URL: `sqlite+aiosqlite:///${path.join(repoRoot, "backend", "test_e2e.db")}`,
        DATABASE_URL_DIRECT: "",
        JWT_SECRET: "test-jwt-secret-key-must-be-32-chars!!",
        GEMINI_API_KEY: "fake",
        OPENAI_API_KEY: "fake",
        MOCK_LLM: "1",
        VAPID_PUBLIC_KEY: "",
        VAPID_PRIVATE_KEY: "",
        VAPID_SUBJECT: "mailto:test@example.com",
      },
    },
    {
      command: "pnpm dev",
      port: 3000,
      cwd: __dirname,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        NEXT_PUBLIC_E2E: "1",
        NEXT_PUBLIC_API_URL: "http://localhost:8000",
      },
    },
  ],
});
