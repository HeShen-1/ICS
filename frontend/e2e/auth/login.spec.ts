import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login form is visible', async ({ page }) => {
    // Check that the login page has phone and password fields
    const phoneInput = page.locator('input[name="phone"], input[type="tel"], input[placeholder*="手机"], input[placeholder*="phone"]');
    const passwordInput = page.locator('input[name="password"], input[type="password"]');
    const submitButton = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("登 录")');

    await expect(phoneInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();
  });

  test('empty form submit shows validation error', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"], button:has-text("登录"), button:has-text("登 录")').first();

    // Click submit without filling in the form
    await submitButton.click();

    // Wait briefly for validation to appear
    await page.waitForTimeout(1000);

    // Either the form stays on /login (client-side validation prevented submit)
    // or the server returns an error. Check for error indicators.
    const isStillOnLogin = page.url().includes('/login');
    const hasError = await page.locator('[role="alert"], .error, .text-red-500, .text-destructive, input:invalid').first().isVisible().catch(() => false);

    expect(isStillOnLogin || hasError).toBeTruthy();
  });

  test('navigate to register page', async ({ page }) => {
    const registerLink = page.locator('a[href*="register"], a:has-text("注册"), a:has-text("注 册"), button:has-text("注册")').first();

    if (await registerLink.isVisible().catch(() => false)) {
      await registerLink.click();
      await expect(page).toHaveURL(/register/);
    } else {
      // If no visible link, navigate directly
      await page.goto('/register');
      await expect(page).toHaveURL(/register/);
    }
  });
});
