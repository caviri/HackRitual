import { defineConfig, devices } from '@playwright/test';

/**
 * Headless screenshot battery for HackRitual.
 *
 * Default target: an already-running site (e.g. the cloudflared tunnel).
 * Override with HACKRITUAL_BASE_URL.
 */
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: 'line',
  use: {
    baseURL: process.env.HACKRITUAL_BASE_URL ?? 'http://localhost:3000',
    screenshot: 'only-on-failure',
    viewport: { width: 1280, height: 800 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
