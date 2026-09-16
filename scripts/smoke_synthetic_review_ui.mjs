#!/usr/bin/env node
/**
 * Browser smoke test for the synthetic Release 1A reviewer journey.
 *
 * Prerequisites:
 *   npm install --prefix .opencode --no-save --no-package-lock playwright@1.62.0
 *
 * Required environment variables (never logged):
 *   SYNTHETIC_REVIEW_LOGIN, SYNTHETIC_REVIEW_PASSWORD, SYNTHETIC_REVIEW_TOTP
 * Optional:
 *   SYNTHETIC_REVIEW_BASE_URL (defaults to http://127.0.0.1:8000)
 */

import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("../.opencode/node_modules/playwright");

const requiredVariables = [
  "SYNTHETIC_REVIEW_LOGIN",
  "SYNTHETIC_REVIEW_PASSWORD",
  "SYNTHETIC_REVIEW_TOTP",
];

if (process.argv.includes("--help")) {
  console.log("Usage: SYNTHETIC_REVIEW_LOGIN=… SYNTHETIC_REVIEW_PASSWORD=… SYNTHETIC_REVIEW_TOTP=… node scripts/smoke_synthetic_review_ui.mjs");
  process.exit(0);
}

const missing = requiredVariables.filter((name) => !process.env[name]);
if (missing.length) {
  console.error(`Missing required environment variables: ${missing.join(", ")}`);
  process.exit(2);
}

const baseUrl = (process.env.SYNTHETIC_REVIEW_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const allowedOrigin = new URL(baseUrl);
if (!["127.0.0.1", "localhost", "[::1]"].includes(allowedOrigin.hostname) || allowedOrigin.protocol !== "http:") {
  console.error("UI_SMOKE_REQUIRES_EXPLICIT_LOOPBACK_TARGET");
  process.exit(2);
}
const url = (path) => `${baseUrl}${path}`;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function login(page) {
  await page.goto(url("/accounts/login/"), { waitUntil: "load" });
  await page.waitForSelector('input[name="login"]', { state: "visible" });
  const localStylesheet = page.locator('link[href*="tailwind-2.2.19.min.css"]');
  assert(await localStylesheet.count(), "login page is missing its local stylesheet");
  const bodyBackground = await page.locator("body").evaluate((body) => getComputedStyle(body).backgroundColor);
  assert(bodyBackground === "rgb(249, 250, 251)", "local stylesheet did not apply the portal background");
  assert((await page.locator('a[href*="signup"]').count()) === 0, "invitation-only login offers sign-up");

  await page.locator('input[name="login"]').fill(process.env.SYNTHETIC_REVIEW_LOGIN);
  await page.locator('input[name="password"]').fill(process.env.SYNTHETIC_REVIEW_PASSWORD);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL("**/accounts/2fa/authenticate/**");
  await page.locator('input[name="code"]').fill(process.env.SYNTHETIC_REVIEW_TOTP);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL("**/review/**");
}

async function reviewChecks(page, viewport) {
  await page.setViewportSize(viewport);
  await page.goto(url("/review/"), { waitUntil: "load" });
  await page.waitForSelector("main, body", { state: "visible" });
  const outcome = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    placeholderLinks: document.querySelectorAll('a[href="#"]').length,
    statusHeights: [...document.querySelectorAll('form button')].slice(0, 3).map((button) => button.getBoundingClientRect().height),
    primary: [...document.querySelectorAll("a")].find((link) => link.textContent.includes("Pokračovat"))?.getBoundingClientRect().toJSON(),
  }));
  assert(!outcome.overflow, `${viewport.width}px review layout has horizontal overflow`);
  assert(outcome.placeholderLinks === 0, "review page contains placeholder links");
  assert(outcome.statusHeights.every((height) => height >= 44), "review status controls are smaller than 44px");
  const minimumPrimaryHeight = viewport.width < 640 ? 44 : 32;
  assert(outcome.primary && outcome.primary.height >= minimumPrimaryHeight, "review primary action is too small");
  return outcome;
}

async function budgetPreviewChecks(page) {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url("/budget/week/"), { waitUntil: "load" });
  await page.waitForSelector("main, body", { state: "visible" });
  const outcome = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    pivotVisible: (() => {
      const table = document.getElementById("pivot-table");
      return !!table && table.offsetParent !== null;
    })(),
    grandTotal: document.getElementById("grand-total")?.textContent.trim(),
    previewControls: [...document.querySelectorAll("button[disabled]")].length,
  }));
  assert(!outcome.overflow, "budget preview has horizontal overflow on mobile");
  assert(!outcome.pivotVisible, "budget pivot is visible on mobile instead of person cards");
  assert(outcome.grandTotal === "2 647,90", "budget fixture totals do not reconcile");
  assert(outcome.previewControls >= 4, "budget preview actions are not clearly disabled");
  return outcome;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ serviceWorkers: "block" });
  const blockedRequests = [];
  await context.route("**/*", (route) => {
    if (new URL(route.request().url()).origin === allowedOrigin.origin) return route.continue();
    blockedRequests.push("EXTERNAL_REQUEST");
    return route.abort();
  });
  const page = await context.newPage();
  const browserErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push("CONSOLE_ERROR");
  });
  page.on("pageerror", (error) => browserErrors.push("PAGE_ERROR"));

  try {
    await page.goto(url("/review/"), { waitUntil: "load" });
    await page.waitForSelector("main, body", { state: "visible" });
    assert(new URL(page.url()).pathname === "/accounts/login/", "anonymous review did not reach login");
    await login(page);
    const mobile = await reviewChecks(page, { width: 390, height: 844 });
    assert(await page.getByRole("link", { name: "Kontrola" }).isVisible(), "mobile review navigation is missing");
    assert(await page.getByRole("link", { name: "Účet" }).isVisible(), "mobile account navigation is missing");

    const desktop = await reviewChecks(page, { width: 1440, height: 1000 });
    const budgetPreview = await budgetPreviewChecks(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url("/review/check-answers/"), { waitUntil: "load" });
    await page.waitForSelector("main, body", { state: "visible" });
    const checkAnswersOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    assert(!checkAnswersOverflow, "answer-check layout has horizontal overflow");

    await page.goto(url("/accounts/logout/"), { waitUntil: "load" });
    await page.locator('button[type="submit"]').click();
    await page.waitForLoadState("load");
    await page.waitForSelector("main, body", { state: "visible" });
    await page.goto(url("/review/"), { waitUntil: "load" });
    await page.waitForSelector("main, body", { state: "visible" });
    assert(new URL(page.url()).pathname === "/accounts/login/", "review remains available after logout");
    assert(browserErrors.length === 0, `browser errors: ${browserErrors.join(" | ")}`);

    assert(blockedRequests.length === 0, "unexpected external resource");
    console.log(JSON.stringify({ result: "pass", mobile, desktop, budgetPreview }));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error("UI_SMOKE_FAILED");
  process.exit(1);
});
