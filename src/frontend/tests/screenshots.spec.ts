import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Screenshot battery — every route × every stage × every theme.
 *
 * Writes PNGs to tests/__screenshots__/ so the gallery survives across runs.
 * The harness is intentionally smoke-style: load the page, wait for any
 * network to settle, snapshot. No assertions about pixels — yet.
 */

const ROUTES = [
  '/',
  '/overview/',
  '/projects/',
  '/projects/3/',
  '/teams/',
  '/teams/the_owls/',
  '/participants/',
  '/participants/ada.cole/',
  '/submissions/',
  '/timeline/',
  '/tracks/data-science/',
  '/pages/rites/',
  '/admin/',
  '/admin/tracks/',
  '/admin/phases/',
  '/admin/pages/',
  '/projects/new/',
  '/teams/new/',
  '/signin/',
];

const STAGES = ['DRAFT', 'OPEN', 'FROZEN', 'FINAL', 'ARCHIVED'] as const;
const THEMES = ['hacker-solarpunk', 'paper-grimoire'] as const;

const OUT = path.join(__dirname, '__screenshots__');
fs.mkdirSync(OUT, { recursive: true });

async function applyTheme(page: Page, theme: string) {
  await page.evaluate(
    (t: string) => {
      document.documentElement.setAttribute('data-theme', t);
      window.localStorage.setItem('hackritual:theme', t);
    },
    theme,
  );
}

async function settle(page: Page) {
  // network idle plus a beat for the staggered ritual-log reveal animation
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
}

for (const route of ROUTES) {
  for (const stage of STAGES) {
    for (const theme of THEMES) {
      const slug =
        route.replace(/^\//, '').replace(/\/$/, '').replace(/\//g, '__') || 'index';
      const name = `${slug}__${stage}__${theme}.png`;

      test(`${route} · ${stage} · ${theme}`, async ({ page }) => {
        await page.goto(`${route}?stage=${stage}`);
        await applyTheme(page, theme);
        await page.reload(); // theme attribute survives via localStorage
        await settle(page);
        await page.screenshot({
          path: path.join(OUT, name),
          fullPage: true,
        });
        expect(true).toBe(true);
      });
    }
  }
}
