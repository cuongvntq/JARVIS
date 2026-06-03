/**
 * Playwright globalSetup — warm up Next.js JIT compilation before tests run.
 *
 * webServer waits for port 3000 to be open, but Next.js dev server JIT-compiles
 * each route on first request. Without warming, the first test navigating to
 * /auth/login triggers compilation (~2-5s) and the subsequent redirect to /
 * triggers another compilation — causing cold-start flakiness.
 *
 * This runs AFTER webServer is ready, BEFORE any test file.
 */
async function globalSetup(): Promise<void> {
  const base = "http://localhost:3000";

  // Trigger compilation for both routes the auth test uses.
  // Errors are ignored — we only care that Next.js compiles, not the response body.
  await Promise.allSettled([
    fetch(`${base}/auth/login`),
    // "/" will redirect to /auth/login via middleware, but the root layout
    // and middleware code get compiled, which is what we need.
    fetch(`${base}/`, { redirect: "follow" }),
  ]);

  // Brief pause so Next.js can finish writing compiled chunks to disk
  await new Promise((resolve) => setTimeout(resolve, 1_000));
}

export default globalSetup;
