import { test, expect } from '@playwright/test'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import AxeBuilder from '@axe-core/playwright'

async function serveSite(page: import('@playwright/test').Page, errors: string[]) {
  const root = path.resolve('../site')
  page.on('pageerror', (e) => errors.push(e.message))
  await page.route('https://digital-himalaya.test/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    const normalized =
      pathname === '/' ? '/index.html' : pathname.endsWith('/') ? `${pathname}index.html` : pathname
    const file = path.resolve(root, '.' + normalized)
    if (!file.startsWith(root + path.sep)) return route.abort()
    const types: Record<string, string> = {
      '.html': 'text/html',
      '.css': 'text/css',
      '.js': 'text/javascript',
      '.svg': 'image/svg+xml',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.mp4': 'video/mp4',
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
}

test('public website explains its limits, diagrams switch, and all local assets resolve', async ({
  page,
}, testInfo) => {
  const errors: string[] = []
  await serveSite(page, errors)
  await page.goto('https://digital-himalaya.test/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Learning shouldn’t')
  await expect(page.getByText('School and curriculum acceptance pending')).toBeVisible()
  await expect(page.getByLabel('Main').getByRole('link', { name: 'Kolibri' })).toHaveAttribute(
    'href',
    'kolibri/',
  )
  await expect(page.locator('.screenshot-gallery img')).toHaveCount(2)
  await expect(page.locator('.screenshot-gallery img').first()).toHaveAttribute(
    'alt',
    /full-width top navigation/,
  )
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
  await page.evaluate(() => window.scrollTo({ top: 900, behavior: 'instant' }))
  await expect
    .poll(() =>
      page.locator('.site-header').evaluate((header) => header.getBoundingClientRect().top),
    )
    .toBe(0)
  await page.getByRole('link', { name: 'The portal' }).click()
  await expect
    .poll(() =>
      page.locator('#preview').evaluate((section) => {
        const header = document.querySelector('.site-header')
        return header
          ? section.getBoundingClientRect().top - header.getBoundingClientRect().bottom
          : -1
      }),
    )
    .toBeGreaterThanOrEqual(0)
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

test('new public pages describe the learner flow and current project state', async ({
  page,
}, testInfo) => {
  const errors: string[] = []
  await serveSite(page, errors)

  await page.goto('https://digital-himalaya.test/how-it-works/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('school library')
  await expect(page.locator('.story-frame')).toHaveCount(5)
  await expect(page.locator('[data-story-frame="1"]')).toHaveAttribute(
    'alt',
    /216 local results, and no default preview/,
  )
  await expect(page.locator('[data-story-frame="2"]')).toHaveAttribute('alt', /CC0/)
  await expect(page.locator('[data-story-frame="4"]')).toHaveAttribute(
    'alt',
    /no channels have been installed yet/,
  )
  await expect
    .poll(() =>
      page
        .locator('.story-frame')
        .evaluateAll((images) =>
          images.every(
            (image) =>
              image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0,
          ),
        ),
    )
    .toBe(true)
  const videoAsset = await page.locator('video source').getAttribute('src')
  expect(videoAsset).toContain('prototype-walkthrough.mp4')
  if (videoAsset === null) throw new Error('The prototype walkthrough source is missing.')
  const videoFetch = await page.evaluate(async (src) => {
    const response = await fetch(new URL(src, location.href))
    const content = await response.arrayBuffer()
    return {
      status: response.status,
      type: response.headers.get('content-type'),
      size: content.byteLength,
    }
  }, videoAsset)
  expect(videoFetch).toEqual({ status: 200, type: 'video/mp4', size: expect.any(Number) })
  expect(videoFetch.size).toBeGreaterThan(100_000)
  for (const index of [0, 1, 2, 3, 4]) {
    const scene = page.locator(`[data-story-step="${index}"]`)
    await scene.evaluate((element) =>
      element.scrollIntoView({ block: 'center', behavior: 'instant' }),
    )
    await expect(scene).toHaveAttribute('aria-current', 'step')
    await expect(page.locator(`[data-story-frame="${index}"]`)).toHaveClass(/is-active/)
    if (index === 1) {
      const stickyTop = await page
        .locator('.story-visual')
        .evaluate((element) => Math.round(element.getBoundingClientRect().top))
      expect(stickyTop).toBeGreaterThanOrEqual(100)
      expect(stickyTop).toBeLessThan(205)
    }
  }
  await expect(
    page.getByRole('list', { name: 'The learner journey' }).getByRole('listitem'),
  ).toHaveCount(4)
  await expect(page.getByText('AI disabled by default · Qdrant unconfigured locally')).toBeVisible()
  await expect(page.getByRole('link', { name: 'How it works' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('how-it-works.png'), fullPage: true })

  await page.getByLabel('Main').getByRole('link', { name: 'Project status' }).click()
  await expect(page).toHaveURL(/\/project\/$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('school pilot still ahead')
  await expect(page.locator('.status-row').first()).toContainText('216 CDC PDFs')
  await expect(page.locator('.status-row').first()).toContainText('Grade 12')
  await expect(page.locator('.verification-list')).toContainText('24')
  await expect(
    page.getByRole('heading', { name: 'Import reviewed Kolibri courses and create school roles' }),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', { name: 'Connect local embeddings and Qdrant' }),
  ).toBeVisible()
  await expect(page.getByRole('link', { name: 'Project status' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('project-status.png'), fullPage: true })

  await page.getByLabel('Main').getByRole('link', { name: 'Kolibri' }).click()
  await expect(page).toHaveURL(/\/kolibri\/$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Ready-made tools')
  for (const material of [
    'Videos',
    'Audio',
    'Documents and books',
    'Exercises',
    'Interactive apps',
  ]) {
    await expect(page.getByRole('heading', { name: material })).toBeVisible()
  }
  await expect(page.locator('.kolibri-status-card > p:last-child')).toContainText(
    'No learning channels, classes, or learner accounts',
  )
  await expect(page.locator('.kolibri-status-card img')).toHaveAttribute(
    'alt',
    /no channels are installed yet/,
  )
  await expect
    .poll(() =>
      page.locator('.kolibri-status-card img').evaluate((image) => {
        return image instanceof HTMLImageElement && image.complete && image.naturalWidth > 0
      }),
    )
    .toBe(true)
  await expect(
    page.getByRole('link', { name: 'Learner materials and activities' }),
  ).toHaveAttribute('href', 'https://kolibri.readthedocs.io/en/latest/learn.html')
  await expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('kolibri-guide.png'), fullPage: true })
  expect(errors).toEqual([])
})
