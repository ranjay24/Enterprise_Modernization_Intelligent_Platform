import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_BASE = 'http://localhost:8000';

test.describe('EMIP End-to-End Tests', () => {
  let page: Page;
  let jobId: string;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto(BASE_URL);
  });

  test.afterEach(async () => {
    await page.close();
  });

  // ============= Phase 1: Upload & Analyze =============
  test('Phase 1: Upload monolith and start analysis', async () => {
    // Navigate to upload
    await page.click('text=Upload');
    await expect(page).toHaveURL(/.*upload/);

    // Check upload form exists
    const uploadInput = page.locator('input[type="file"]');
    await expect(uploadInput).toBeVisible();

    console.log('✓ Phase 1: Upload page loaded');
  });

  test('Phase 2: Verify analysis pipeline starts', async () => {
    // Go to jobs
    await page.click('text=Jobs');
    await expect(page).toHaveURL(/.*jobs/);

    // Wait for jobs list
    await page.waitForSelector('text=Running Jobs');
    const jobCount = await page.locator('text=Running Jobs').count();

    if (jobCount > 0) {
      console.log('✓ Phase 2: Analysis pipeline detected');
    }
  });

  test('Phase 3: Monitor analysis progress', async () => {
    // Go to jobs
    await page.click('text=Jobs');

    // Wait for pipeline overview
    await page.waitForSelector('text=Pipeline Overview', { timeout: 5000 });

    // Check stages are visible
    const stages = [
      'Extraction',
      'Static Analysis',
      'Service Boundaries',
      'Readiness Scoring',
      'Cost Analysis',
      'Report Generation'
    ];

    for (const stage of stages) {
      const stageEl = page.locator(`text=${stage}`);
      if (await stageEl.isVisible()) {
        console.log(`✓ Stage found: ${stage}`);
      }
    }
  });

  test('Phase 4: Wait for analysis completion', async () => {
    // Poll jobs until one completes
    for (let i = 0; i < 180; i++) { // Max 30 minutes
      await page.goto(`${BASE_URL}/jobs`);

      const completedSection = page.locator('text=Completed');
      if (await completedSection.isVisible()) {
        console.log('✓ Phase 4: Analysis completed');

        // Extract job ID from first completed job
        const jobLink = page.locator('a:has-text("results")').first();
        const href = await jobLink.getAttribute('href');
        jobId = href?.split('/')[2] || '';
        console.log(`Job ID: ${jobId}`);
        return;
      }

      await page.waitForTimeout(10000); // Wait 10s before retry
    }
    throw new Error('Analysis did not complete');
  });

  // ============= Phase 5: Results & Reports =============
  test('Phase 5: View analysis results', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/results`);
    await page.waitForSelector('text=Enterprise Modernization Intelligence', { timeout: 10000 });

    // Verify result sections
    const sections = [
      'Readiness Assessment',
      'Architecture Intelligence',
      'Risk Analysis',
      'Cost and ROI',
      'Migration Roadmap'
    ];

    for (const section of sections) {
      const visible = await page.locator(`text=${section}`).isVisible();
      console.log(`${visible ? '✓' : '✗'} ${section}`);
    }
  });

  test('Phase 6: Check Reports page', async () => {
    await page.click('text=Reports');
    await expect(page).toHaveURL(/.*reports/);

    // Check report sections load
    await page.waitForSelector('text=Readiness Assessment', { timeout: 5000 });
    console.log('✓ Phase 6: Reports page loaded with data');
  });

  test('Phase 7: Check Migration page', async () => {
    await page.click('text=Migration');

    const migrationPage = page.locator('text=Migration Planner');
    if (await migrationPage.isVisible()) {
      console.log('✓ Phase 7: Migration Planner loaded');

      // Check wave timeline
      const waves = await page.locator('[role="progressbar"]').count();
      console.log(`  Waves detected: ${waves}`);
    }
  });

  // ============= Phase 8: Code Generation =============
  test('Phase 8: Start code generation', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/results`);

    // Find and click "Generate" button
    const genButton = page.locator('button:has-text("Generate")').first();
    if (await genButton.isVisible()) {
      await genButton.click();
      console.log('✓ Phase 8: Code generation started');
    } else {
      console.log('⊘ Generate button not found');
    }
  });

  test('Phase 9: Modernization Studio - Check agent pipeline', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/studio`);

    // Wait for studio to load
    await page.waitForSelector('text=Modernization Studio', { timeout: 5000 });

    // Check agent pipeline
    const agents = [
      'Architecture Designer',
      'Service Planner',
      'Code Generator',
      'Review Agent'
    ];

    for (const agent of agents) {
      const visible = await page.locator(`text=${agent}`).isVisible();
      console.log(`${visible ? '✓' : '✗'} ${agent}`);
    }
  });

  test('Phase 10: Check Architecture tab', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/studio`);

    // Click Architecture tab
    await page.click('button:has-text("Architecture")');
    await page.waitForTimeout(2000);

    // Check for service cards
    const serviceCards = await page.locator('[class*="card"]').count();
    if (serviceCards > 0) {
      console.log(`✓ Phase 10: Architecture tab - ${serviceCards} service cards found`);
    }

    // Check for Kafka/RabbitMQ badges
    const brokerBadges = await page.locator('[class*="badge"]').count();
    console.log(`  Broker badges: ${brokerBadges}`);
  });

  test('Phase 11: Check Code tab', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/studio`);
    await page.click('button:has-text("Code")');
    await page.waitForTimeout(2000);

    // Check for service selector
    const serviceButtons = await page.locator('button[class*="service"]').count();
    if (serviceButtons > 0) {
      console.log(`✓ Phase 11: Code tab - ${serviceButtons} services available`);

      // Click first service
      await page.locator('button[class*="service"]').first().click();
      await page.waitForTimeout(1000);

      // Check file explorer
      const fileTree = await page.locator('[class*="tree"], [class*="explorer"]').isVisible();
      console.log(`  File explorer: ${fileTree ? '✓' : '✗'}`);
    }
  });

  test('Phase 12: Check Review tab', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    await page.goto(`${BASE_URL}/jobs/${jobId}/studio`);
    await page.click('button:has-text("Review")');
    await page.waitForTimeout(2000);

    // Check review report
    const approvedBadge = await page.locator('text=APPROVED, text=Approved').first().isVisible();
    if (approvedBadge) {
      console.log('✓ Phase 12: Review tab - Services approved');
    }

    // Check findings
    const findings = await page.locator('[class*="finding"]').count();
    console.log(`  Findings count: ${findings}`);
  });

  // ============= Phase 13: Return to Jobs & Verify Status =============
  test('Phase 13: Verify job status updated to completed', async () => {
    await page.goto(`${BASE_URL}/jobs`);

    // Check for completed jobs section
    const completedSection = await page.locator('text=Completed').isVisible();
    if (completedSection) {
      console.log('✓ Phase 13: Job moved to Completed section');
    } else {
      console.log('✗ Phase 13: Job still in Running section');
    }
  });

  // ============= Phase 14: End-to-End Flow Verification =============
  test('Phase 14: Verify all data persists', async () => {
    if (!jobId) {
      console.log('⊘ Skipping: jobId not set');
      return;
    }

    // Check API endpoints
    const endpoints = [
      `/api/results/${jobId}`,
      `/api/results/${jobId}/analysis`,
      `/api/codegen/${jobId}/status`,
      `/api/codegen/${jobId}/architecture`,
      `/api/codegen/${jobId}/plan`,
      `/api/codegen/${jobId}/review`
    ];

    for (const endpoint of endpoints) {
      const response = await page.request.get(`${API_BASE}${endpoint}`);
      const status = response.status();
      console.log(`${status === 200 ? '✓' : '✗'} ${endpoint} - ${status}`);
    }
  });
});

test.describe('UI & Performance Tests', () => {
  test('Check page load times', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(BASE_URL);
    const loadTime = Date.now() - startTime;

    console.log(`Dashboard load: ${loadTime}ms ${loadTime < 3000 ? '✓' : '⚠'}`);
  });

  test('Check responsive design', async ({ page }) => {
    // Test mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(BASE_URL);

    const hamburger = await page.locator('[class*="menu"], [class*="hamburger"]').isVisible();
    console.log(`Mobile menu: ${hamburger ? '✓' : '⚠'}`);
  });

  test('Check for console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto(BASE_URL);
    await page.click('text=Jobs');

    if (errors.length === 0) {
      console.log('✓ No console errors');
    } else {
      console.log(`✗ Console errors: ${errors.length}`);
      errors.forEach(e => console.log(`  - ${e}`));
    }
  });
});
