import { test, expect } from '@playwright/test';

// Authentication-gate walkthrough.
//
// Runs against the Vite dev server with the backend auth probe /api/auth/me
// route-mocked, so the gate logic is exercised deterministically without a live
// backend. Each test starts from a clean localStorage (no demo flag, no
// tokens).
//
// Auth model: with the built-in local auth provider enabled (the default), an
// unauthenticated probe returns 401 → the app gates to /login. A 503 (every
// provider disabled) preserves the old guest/no-login behavior.

function notConfigured() {
  return {
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Authentication is not configured on this deployment' }),
  };
}

function notAuthenticated() {
  return {
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Not authenticated' }),
  };
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
  });
});

test.describe('Authentication gate', () => {
  test('Auth not configured (503) → guest session, no login gate', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notConfigured()));
    await page.goto('/dashboard');
    await expect(page).not.toHaveURL(/\/login$/);
    await expect(page.locator('main').getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('No token → redirected to the login page', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notAuthenticated()));
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Continue in Demo Mode' })).toBeVisible();
  });

  test('Login page demo bypass drops into the demo dashboard', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notAuthenticated()));
    await page.goto('/login');
    await page.getByRole('button', { name: 'Continue in Demo Mode' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText(/Demo Mode is on/)).toBeVisible();
  });

  test('Successful login stores the session and shows the user chip', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notAuthenticated()));
    await page.route('**/api/auth/login', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'at-123',
          id_token: 'id-token-123',
          refresh_token: 'rt-123',
          expires_in: 3600,
          user: { username: 'alice', email: 'alice@emip.io', name: 'Alice Smith' },
        }),
      })
    );
    await page.goto('/login');
    await page.getByLabel('Email').fill('alice@emip.io');
    await page.getByLabel('Password', { exact: true }).fill('DemoPass123!');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(page.getByText('Alice Smith').first()).toBeVisible();
  });

  test('Signup page renders and rejects mismatched passwords', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notAuthenticated()));
    await page.goto('/signup');
    await expect(page.getByRole('heading', { name: 'Create an account' })).toBeVisible();
    await page.getByLabel('Username', { exact: true }).fill('jdoe');
    await page.getByLabel('Email', { exact: true }).fill('jdoe@emip.io');
    await page.getByLabel('Password', { exact: true }).fill('DemoPass123');
    await page.getByLabel('Confirm password', { exact: true }).fill('Different123');
    await page.getByRole('button', { name: 'Create account' }).click();
    await expect(page.getByText('Passwords do not match')).toBeVisible();
  });

  test('Signup shows the dev verification code on the verify step', async ({ page }) => {
    await page.route('**/api/auth/me', (route) => route.fulfill(notAuthenticated()));
    await page.route('**/api/auth/signup', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Account created. Check your email for a verification code.',
          verification_code: '482913',
        }),
      })
    );
    await page.goto('/signup');
    await page.getByLabel('Username', { exact: true }).fill('jdoe');
    await page.getByLabel('Email', { exact: true }).fill('jdoe@emip.io');
    await page.getByLabel('Password', { exact: true }).fill('DemoPass123');
    await page.getByLabel('Confirm password', { exact: true }).fill('DemoPass123');
    await page.getByRole('button', { name: 'Create account' }).click();
    await expect(page.getByRole('heading', { name: 'Verify your email' })).toBeVisible();
    await expect(page.getByText('Development mode')).toBeVisible();
    await expect(page.getByText('482913')).toBeVisible();
  });
});
