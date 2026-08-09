import { test, expect } from '@playwright/test';

// Demo-mode smoke walkthrough (P7.7).
//
// Runs entirely against the Vite dev server in demo mode: no live backend, no
// 30-minute polls, no console.log soft-checks. Every step is a hard assertion.
// The walkthrough mirrors the demo product flow: dashboard → upload (real ZIP
// validation) → jobs (sample analyses) → results (full sample report).
//
// Demo mode is enabled per-page before app boot via sessionStorage (emip-demo),
// matching useAppStore.getInitialDemoMode(). The sidebar preference stays in
// localStorage (emip-sidebar).

const DEMO_JOB_ID = 'job-bank-003';

// Minimal, valid ZIP magic bytes (PK\x03\x04) so real client-side validation passes.
function zipBuffer(): Buffer {
  return Buffer.concat([Buffer.from([0x50, 0x4b, 0x03, 0x04]), Buffer.alloc(64, 0)]);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('emip-demo', 'true');
    localStorage.setItem('emip-sidebar', 'false');
  });
});

test.describe('Demo-mode smoke walkthrough', () => {
  test('Dashboard renders with the honest demo banner', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.locator('main').getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText(/Demo Mode is on/)).toBeVisible();
  });

  test('Sidebar "Analyze Code" navigates to the upload page', async ({ page }) => {
    await page.goto('/dashboard');
    await page.locator('aside').getByRole('link', { name: 'Analyze Code' }).click();
    await expect(page).toHaveURL(/\/upload$/);
    await expect(
      page.getByRole('heading', { name: 'Start a Modernization Assessment' })
    ).toBeVisible();
  });

  test('Upload page renders a real file picker', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.getByRole('heading', { name: 'Start a Modernization Assessment' })).toBeVisible();
    // The native input is intentionally hidden; the visible drop zone is the picker surface.
    await expect(page.getByRole('button', { name: 'Drop zone for ZIP files' })).toBeVisible();
    await expect(page.locator('input[type="file"][accept=".zip"]')).toBeAttached();
  });

  test('Upload: a valid ZIP passes client validation and shows the project form', async ({ page }) => {
    await page.goto('/upload');
    await page.setInputFiles('input[type="file"]', {
      name: 'demo-project.zip',
      mimeType: 'application/zip',
      buffer: zipBuffer(),
    });
    await expect(page.getByRole('button', { name: /Start Upload & Analysis/ })).toBeVisible();
  });

  test('Upload: a non-ZIP file is rejected with a clear error', async ({ page }) => {
    await page.goto('/upload');
    await page.setInputFiles('input[type="file"]', {
      name: 'readme.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('not a zip'),
    });
    await expect(page.getByText('Only .zip files are supported')).toBeVisible();
  });

  test('Upload with no backend fails honestly instead of faking success', async ({ page }) => {
    // Force a network failure for the upload call so the test is deterministic
    // even when a live backend happens to be running.
    await page.route('**/api/upload', (route) => route.abort());
    await page.goto('/upload');
    await page.setInputFiles('input[type="file"]', {
      name: 'demo-project.zip',
      mimeType: 'application/zip',
      buffer: zipBuffer(),
    });
    await page.getByRole('button', { name: /Start Upload & Analysis/ }).click();
    await expect(
      page.getByText(/Network Error|Upload Failed|Service Unavailable/).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('Jobs page shows sample jobs with the demo banner', async ({ page }) => {
    await page.goto('/jobs');
    await expect(page.locator('main').getByRole('heading', { name: 'Jobs', exact: true })).toBeVisible();
    await expect(page.getByText(/Running Jobs/)).toBeVisible();
    await expect(page.getByText('Banking Core').first()).toBeVisible();
    await expect(page.getByText(/Demo Mode is on/)).toBeVisible();
  });

  test('Results page renders the full sample analysis', async ({ page }) => {
    await page.goto(`/jobs/${DEMO_JOB_ID}/results`);
    await expect(
      page.getByRole('heading', { name: 'Enterprise Modernization Intelligence' })
    ).toBeVisible();
    await expect(page.getByText(/Demo Mode is on/)).toBeVisible();
    await expect(page.getByText('Readiness Assessment').first()).toBeVisible();
    await expect(page.getByText('Architecture Intelligence').first()).toBeVisible();
    await expect(page.getByText(/Analysis Complete/).first()).toBeVisible();
  });

  test('Migration Planner renders', async ({ page }) => {
    await page.goto('/migration');
    await expect(page.locator('main').getByRole('heading', { name: 'Migration Planner' })).toBeVisible();
  });

  test('Reports page renders', async ({ page }) => {
    await page.goto('/reports');
    await expect(page.locator('main').getByRole('heading', { name: 'Reports' })).toBeVisible();
  });

  test('Modernization Studio renders', async ({ page }) => {
    await page.goto('/studio');
    await expect(page.locator('main').getByRole('heading', { name: 'Modernization Studio' })).toBeVisible();
  });

  test('Architecture page renders', async ({ page }) => {
    await page.goto('/architecture');
    await expect(page.locator('main').getByRole('heading', { name: 'Architecture' })).toBeVisible();
  });

  test('Core demo walkthrough produces no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/dashboard');
    await page.goto('/upload');
    await page.goto('/jobs');
    await page.goto(`/jobs/${DEMO_JOB_ID}/results`);
    await page.waitForLoadState('networkidle');

    expect(errors, `Console errors:\n${errors.join('\n')}`).toEqual([]);
  });
});
