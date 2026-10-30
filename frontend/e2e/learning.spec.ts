import { expect, test } from '@playwright/test'

const token = 'test-only-staff-token-that-is-not-a-real-secret'

test('home has truthful services, works in Nepali, and has no horizontal overflow', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByText('School server connected', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Offline Wikipedia' })).toBeVisible()
  await expect(page.getByText('Not configured', { exact: true })).toHaveCount(1)
  await expect(page.getByRole('link', { name: /Kolibri courses/ })).toHaveAttribute(
    'href',
    'http://kolibri.test:8080',
  )
  await expect(page.getByRole('link', { name: /Staff/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Offline Wikipedia/ })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('radio', { name: 'नेपाली' }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'ne')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('खोज्न बाँकी संसार')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(errors).toEqual([])
})

test('staff import flows through the API, books open, and tutor shows real retrieval metadata', async ({
  page,
}) => {
  await page.goto('/staff')
  await page.getByLabel('Staff access token').fill('wrong')
  await page.getByRole('button', { name: 'Open staff workspace' }).click()
  await expect(page.getByRole('alert')).toContainText('Staff sign-in required')
  await page.getByLabel('Staff access token').fill(token)
  await page.getByRole('button', { name: 'Open staff workspace' }).click()
  await expect(page.getByRole('heading', { name: 'Import a chapter' })).toBeVisible()
  await page.getByLabel('Document title').fill('E2E force and motion')
  await page.getByLabel('Chapter', { exact: true }).fill('Force and Motion')
  await page.getByLabel('License / permission').fill('CC0-1.0')
  await page.getByLabel('Source / attribution').fill('Original browser test fixture')
  await page.getByLabel('PDF or UTF-8 text file').setInputFiles({
    name: 'force.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Newton’s second law: force equals mass times acceleration.'),
  })
  await page.getByRole('button', { name: 'Import and index' }).click()
  await expect(page.getByRole('status')).toHaveText('Document ready in the library.')
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 })
  await page.getByRole('link', { name: 'My textbooks', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'E2E force and motion' })).toBeVisible()
  const fileUrl = await page.getByRole('link', { name: 'Open textbook' }).getAttribute('href')
  const file = await page.request.get(fileUrl!)
  expect(file.status()).toBe(200)
  expect(await file.text()).toContain('Newton')
  await page.getByRole('link', { name: 'AI tutor', exact: true }).click()
  await page.getByLabel('Chapter', { exact: true }).selectOption('Force and Motion')
  await page.getByLabel('Your question').fill('Explain force and mass.')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  await expect(page.getByText('Textbook passages retrieved', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'E2E force and motion, pages 1' })).toHaveAttribute(
    'href',
    /\/api\/textbooks\/[a-f0-9]{32}\/file#page=1/,
  )
  await page.getByLabel('Grade', { exact: true }).selectOption('9')
  await expect(page.getByText('Test model output.', { exact: false })).toHaveCount(0)
  await page.getByLabel('Your question').fill('Explain force without a Grade 9 source.')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  await expect(
    page.getByText('General explanation - no matching textbook passage', { exact: true }),
  ).toBeVisible()
  await expect(page.locator('.sources a')).toHaveCount(0)
  await page.reload()
  await expect(page.getByText('Every good question is a place to start.')).toBeVisible()
})

test('tutor outage is visible and preserves the question for retry', async ({ page }) => {
  await page.route('**/api/tutor/chat', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'The local model is unavailable.' }),
    }),
  )
  await page.goto('/tutor')
  await page.getByLabel('Your question').fill('Why does a cart accelerate?')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  await expect(page.getByRole('alert')).toContainText('The local model is unavailable.')
  await expect(page.getByLabel('Your question')).toHaveValue('Why does a cart accelerate?')
  await expect(page.locator('.message.assistant')).toHaveCount(0)
})

test('portal shows a disconnected server and allows retry', async ({ page }) => {
  await page.route('**/api/services', (route) => route.abort())
  await page.goto('/')
  await expect(page.getByText('School server unreachable', { exact: true })).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('Check school Wi-Fi')
  await page.unroute('**/api/services')
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByText('School server connected', { exact: true })).toBeVisible()
})

test('keyboard navigation reaches the learning content', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'What would you like to learn?' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main')).toBeInViewport()
})
