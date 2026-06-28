import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    // Wait for the chat page to render (protected route loads after auth)
    await page.waitForTimeout(2000);
  });

  test('chat interface is visible', async ({ page }) => {
    // The chat page should have an input area and a message area
    const inputArea = page.locator('textarea, input[type="text"], [contenteditable="true"], [role="textbox"]');
    const sendButton = page.locator('button[aria-label*="发送"], button[aria-label*="send"], button:has(svg)').first();

    // At least one interactive element should be visible on the chat page
    const hasInput = await inputArea.first().isVisible().catch(() => false);
    const hasSendButton = await sendButton.isVisible().catch(() => false);

    // The page should be the chat page (not redirected to login)
    expect(page.url()).toContain('/chat');
    expect(hasInput || hasSendButton).toBeTruthy();
  });

  test('sidebar is visible', async ({ page }) => {
    // The sidebar contains navigation or session list
    const sidebar = page.locator('aside, nav, [class*="sidebar"], [class*="Sidebar"], [class*="side"]');
    const newChatButton = page.locator('button:has-text("新对话"), button:has-text("新建"), button:has-text("New"), button[aria-label*="new" i]');

    const hasSidebar = await sidebar.first().isVisible().catch(() => false);
    const hasNewChat = await newChatButton.first().isVisible().catch(() => false);

    // At least sidebar or new-chat button should be visible
    expect(hasSidebar || hasNewChat).toBeTruthy();
  });
});
