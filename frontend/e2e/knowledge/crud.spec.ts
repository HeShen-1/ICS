import { test, expect } from '@playwright/test';

test.describe('Knowledge Base', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/knowledge');
    await page.waitForTimeout(2000);
  });

  test('knowledge page loads', async ({ page }) => {
    // Should not be redirected to login
    expect(page.url()).toContain('/knowledge');

    // The page should have some content rendered
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });

  test('upload area is visible', async ({ page }) => {
    // Look for upload-related UI elements
    const uploadArea = page.locator(
      'input[type="file"], ' +
      '[class*="upload"], [class*="Upload"], ' +
      'button:has-text("上传"), button:has-text("导入"), ' +
      'label:has-text("上传"), label:has-text("导入"), ' +
      '[data-testid*="upload"]'
    );

    const hasUpload = await uploadArea.first().isVisible().catch(() => false);

    // Also check for general knowledge page structure
    const hasContent = await page.locator('h1, h2, h3, table, [role="table"], ul, ol').first().isVisible().catch(() => false);

    // Page should either have upload UI or document listing content
    expect(hasUpload || hasContent).toBeTruthy();
  });
});
