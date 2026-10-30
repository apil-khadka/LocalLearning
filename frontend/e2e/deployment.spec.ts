import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('production bundle runs locally, with separate student and staff boundaries', async ({
  page,
  request,
}, testInfo) => {
  test.skip(!process.env.DEPLOYMENT_URL, 'Set DEPLOYMENT_URL to test the built containers')
  const base = process.env.DEPLOYMENT_URL!
  const errors: string[] = []
  const externalRequests: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  await page.route('**/*', (route) => {
    if (new URL(route.request().url()).origin !== new URL(base).origin) {
      externalRequests.push(route.request().url())
      return route.abort()
    }
    return route.continue()
  })
  await page.goto(base)
  await expect(page.getByText('School server connected', { exact: true })).toBeVisible()
  await expect(page.getByText('Teacher review required', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(
    (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze())
      .violations,
  ).toEqual([])
  await page.screenshot({ path: testInfo.outputPath('portal.png'), fullPage: true })
  await page.getByRole('radio', { name: 'नेपाली' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('खोज्न बाँकी संसार')
  await page.getByRole('link', { name: 'एआई शिक्षक', exact: true }).click()
  await expect(page.getByLabel('तपाईंको प्रश्न')).toBeVisible()
  expect((await request.get(base + '/api/admin/index-status')).status()).toBe(403)
  expect((await request.get(base + '/staff')).status()).toBe(404)
  expect((await request.get(base + '/staff/')).status()).toBe(404)
  expect(externalRequests).toEqual([])
  expect(errors).toEqual([])
})
