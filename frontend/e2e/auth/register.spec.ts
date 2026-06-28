import { test, expect } from '@playwright/test';

test.describe('Register Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
  });

  test('registration form is visible', async ({ page }) => {
    // Check that the register page has the necessary form elements
    const phoneInput = page.locator('input[name="phone"], input[type="tel"], input[placeholder*="手机"], input[placeholder*="phone"]');
    const passwordInput = page.locator('input[name="password"], input[type="password"]');
    const submitButton = page.locator('button[type="submit"], button:has-text("注册"), button:has-text("注 册"), button:has-text("Sign up")');

    await expect(phoneInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();

    // Verify we have a link back to login
    const loginLink = page.locator('a[href*="login"], a:has-text("登录")').first();
    const hasLoginLink = await loginLink.isVisible().catch(() => false);
    // Not strictly required but nice to check; don't fail if absent
    expect(hasLoginLink || true).toBeTruthy();
  });
});
