// Screenshot the static export in demo mode.
//
// Serves frontend/out over HTTP (Next's absolute asset paths need a real
// origin, not file://) and drives chromium over a small set of routes. With no
// backend reachable the app falls back to its bundled demo data, so the pages
// render fully populated — ideal for a README gallery.
//
// Run inside the version-matched Playwright image:
//   docker run --rm -v <repo>:/repo -w /repo/frontend \
//     mcr.microsoft.com/playwright:v1.47.2-jammy node scripts/shots.mjs

import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const ROOT = path.resolve('out');
const OUT_DIR = path.resolve('..', 'docs', 'screenshots');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain',
};

function resolveFile(urlPath) {
  const clean = decodeURIComponent(urlPath.split('?')[0]);
  const candidates = [
    path.join(ROOT, clean),
    path.join(ROOT, clean, 'index.html'),
    path.join(ROOT, `${clean}.html`),
  ];
  for (const c of candidates) {
    try {
      if (existsSync(c) && statSync(c).isFile()) return c;
    } catch {
      /* fall through */
    }
  }
  return null;
}

const server = http.createServer(async (req, res) => {
  let file = resolveFile(req.url);
  // SPA-ish fallback for trailing-slash directory routes.
  if (!file) {
    const dirIndex = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]), 'index.html');
    if (existsSync(dirIndex)) file = dirIndex;
  }
  if (!file) {
    res.writeHead(404);
    res.end('not found');
    return;
  }
  const body = await readFile(file);
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] ?? 'application/octet-stream' });
  res.end(body);
});

const PAGES = [
  { route: '/', name: 'home' },
  { route: '/overview/', name: 'overview' },
  { route: '/leaderboard/', name: 'leaderboard' },
  { route: '/projects/', name: 'projects' },
  { route: '/submissions/', name: 'submissions' },
  { route: '/admin/', name: 'admin' },
  { route: '/signin/', name: 'signin' },
];

await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const base = `http://127.0.0.1:${port}`;
console.log(`serving ${ROOT} at ${base}`);

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
});

for (const { route, name } of PAGES) {
  const url = `${base}${route}`;
  await page.goto(url, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1200); // let client fetches settle into demo data
  const dest = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: dest, fullPage: false });
  console.log(`✓ ${route} → docs/screenshots/${name}.png`);
}

await browser.close();
server.close();
console.log('done');
