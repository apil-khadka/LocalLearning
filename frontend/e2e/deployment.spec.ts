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
  if (process.env.KOLIBRI_PUBLIC_URL) {
    await expect(page.getByRole('link', { name: /Kolibri courses/ })).toHaveAttribute(
      'href',
      process.env.KOLIBRI_PUBLIC_URL,
    )
  }
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

test('production tutor renders the model Markdown as formatted content', async ({ page }) => {
  test.skip(!process.env.DEPLOYMENT_URL, 'Set DEPLOYMENT_URL to test the built containers')
  const base = process.env.DEPLOYMENT_URL!
  const answer = [
    'No matching textbook passage was found, so this is a **general explanation, not a textbook answer**.',
    '',
    '### Why do plants need sunlight?',
    '',
    'Plants need sunlight to make their own food. This process is called **photosynthesis**.',
    '',
    '1. Carbon dioxide from the air',
    '2. Water from the soil',
  ].join('\n')

  await page.route('**/api/tutor/chat', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ answer, grounding: 'general', model: 'test-model', sources: [] }),
    }),
  )
  await page.goto(`${base}/tutor`)
  await page.getByLabel('Your question').fill('Why do plants need sunlight?')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()

  const content = page.locator('.message.assistant .message-content')
  await expect(content.locator('strong')).toHaveText([
    'general explanation, not a textbook answer',
    'photosynthesis',
  ])
  await expect(content.locator('h3')).toHaveText('Why do plants need sunlight?')
  await expect(content.locator('ol li')).toHaveText([
    'Carbon dioxide from the air',
    'Water from the soil',
  ])
  await expect(content).not.toContainText(/\*\*|^###/)
})

test('production app shell asks the browser to revalidate its HTML', async ({ request }) => {
  test.skip(!process.env.DEPLOYMENT_URL, 'Set DEPLOYMENT_URL to test the built containers')
  const base = process.env.DEPLOYMENT_URL!
  for (const path of ['/', '/tutor']) {
    const response = await request.get(new URL(path, base).toString())
    expect(response.ok()).toBe(true)
    expect(response.headers()['cache-control']).toContain('no-cache')
  }
})
