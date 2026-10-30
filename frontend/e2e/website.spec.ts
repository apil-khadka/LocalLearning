import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'

test('public website explains its limits, diagrams switch, and all local assets resolve', async ({
  page,
}, testInfo) => {
  const root = path.resolve('../site')
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.route('https://digital-himalaya.test/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname))
    if (!file.startsWith(root + path.sep)) return route.abort()
    const types: Record<string, string> = {
      '.html': 'text/html',
      '.css': 'text/css',
      '.js': 'text/javascript',
      '.svg': 'image/svg+xml',
      '.png': 'image/png',
      '.woff2': 'font/woff2',
    }
    try {
      await route.fulfill({
        status: 200,
        contentType: types[path.extname(file)] ?? 'text/plain',
        body: await readFile(file),
      })
    } catch {
      errors.push('Missing local asset: ' + pathname)
      await route.fulfill({ status: 404 })
    }
  })
  await page.goto('https://digital-himalaya.test/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Learning shouldn’t')
  await expect(page.getByText('Field and real-model acceptance pending')).toBeVisible()
  await expect(page.locator('.screenshot-gallery img')).toHaveCount(2)
  await page.locator('.screenshot-gallery').scrollIntoViewIfNeeded()
  await expect
    .poll(() =>
      page
        .locator('.screenshot-gallery img')
        .evaluateAll((images) =>
          images.every(
            (image) =>
              image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0,
          ),
        ),
    )
    .toBe(true)
  await page.getByRole('button', { name: 'A tutor question' }).click()
  await expect(page.locator('#network-flow')).toContainText('Selected chat provider')
  await expect(page.locator('#network-caption')).toContainText('hosted provider receives')
  await expect(page.getByRole('button', { name: 'A tutor question' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('button', { name: 'Staff administration' }).click()
  await expect(page.locator('#network-flow')).toContainText('SSH tunnel')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  const missingAnchors = await page
    .locator('a[href^="#"]')
    .evaluateAll((links) =>
      links
        .filter((link) => !document.querySelector(link.getAttribute('href')!))
        .map((link) => link.getAttribute('href')),
    )
  expect(missingAnchors).toEqual([])
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('website.png'), fullPage: true })
  expect(errors).toEqual([])
})
