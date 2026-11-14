import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function signIn(
  page: Page,
  base: string,
  username = process.env.DEPLOYMENT_USERNAME,
  password = process.env.DEPLOYMENT_PASSWORD,
) {
  test.skip(!username || !password, 'Set deployment credentials for authenticated Docker checks')
  await page.goto(`${base}/login`)
  await page.getByLabel('Username').fill(username!)
  await page.getByLabel('Password').fill(password!)
  const response = page.waitForResponse(
    (item) => item.url().includes('/api/auth/login') && item.request().method() === 'POST',
  )
  await page.locator('form.account-form').getByRole('button', { name: 'Sign in' }).first().click()
  expect((await response).status()).toBe(200)
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}

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
    if (message.type() === 'error' && !message.text().includes('401 (Unauthorized)')) {
      errors.push(message.text())
    }
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
  const servicesResponse = await request.get(`${base}/api/services`)
  expect(servicesResponse.status()).toBe(200)
  const services = await servicesResponse.json()
  const tutorStatusCopy: Record<string, string> = {
    ready: 'Available',
    configured: 'Configured; connection checked on first question',
    disabled: 'Teacher review required',
    unavailable: 'Unavailable',
    unconfigured: 'Not configured',
    missing_model: 'Model not installed',
  }
  await expect(
    page.getByText(tutorStatusCopy[services.tutor.status] ?? 'Unavailable', { exact: true }),
  ).toBeVisible()
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
  await signIn(page, base)
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'My learning' })).toBeVisible()
  await page.getByRole('link', { name: 'Learning home', exact: true }).click()
  await page.getByRole('radio', { name: 'नेपाली' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('खोज्न बाँकी संसार')
  await page.getByRole('link', { name: 'एआई शिक्षक', exact: true }).click()
  await expect(page.getByLabel('तपाईंको प्रश्न')).toBeVisible()
  expect((await request.get(base + '/api/admin/index-status')).status()).toBe(403)
  expect((await request.get(base + '/staff')).status()).toBe(404)
  expect((await request.get(base + '/staff/')).status()).toBe(404)
  const previewPolicy = await request.get(
    `${base}/api/textbooks/00000000000000000000000000000000/file`,
  )
  expect(previewPolicy.status()).toBe(404)
  expect(previewPolicy.headers()['content-security-policy']).toBe(
    "default-src 'none'; frame-ancestors 'self'",
  )
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
  await signIn(page, base)
  await page.goto(`${base}/tutor`)
  const subject = page.getByLabel('Subject', { exact: true })
  await expect(subject).toHaveJSProperty('tagName', 'SELECT')
  await expect(subject.getByRole('option', { name: 'Science', exact: true })).toBeAttached()
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

test('Docker staff listener supports administrator account recovery controls', async ({ page }) => {
  const base = process.env.DEPLOYMENT_STAFF_URL
  const username = process.env.DEPLOYMENT_ADMIN_USERNAME
  const password = process.env.DEPLOYMENT_ADMIN_PASSWORD
  test.skip(
    !base || !username || !password,
    'Set staff listener and administrator test credentials',
  )
  await signIn(page, base!, username, password)
  await expect(page).toHaveURL(/\/teacher$/)
  const createdUsername = `docker-qa-${Date.now()}`
  const teacherForm = page
    .locator('form.account-form')
    .filter({ hasText: 'Create teacher account' })
  await teacherForm.getByLabel('Name shown in school').fill('Docker QA Teacher')
  await teacherForm.getByLabel('Username').fill(createdUsername)
  await teacherForm.getByLabel('Password').fill('Docker-QA-Teacher-2026!')
  await teacherForm.getByRole('button', { name: 'Create teacher account' }).click()
  const accountRow = page.locator('.learner-list li').filter({ hasText: createdUsername })
  await expect(accountRow).toBeVisible()
  await accountRow.getByRole('button', { name: 'Reset password' }).click()
  await expect(accountRow.locator('.temporary-credential')).toContainText('Temp-')
  await accountRow.getByRole('button', { name: 'Deactivate' }).click()
  await expect(accountRow).toContainText('Account disabled')
  await accountRow.getByRole('button', { name: 'Restore' }).click()
  await expect(accountRow).toContainText('Must change initial password')
})

test('Docker admin sign-in from the student listener redirects to staff', async ({ page }) => {
  const base = process.env.DEPLOYMENT_URL
  const staffBase = process.env.DEPLOYMENT_STAFF_URL
  const username = process.env.DEPLOYMENT_ADMIN_USERNAME
  const password = process.env.DEPLOYMENT_ADMIN_PASSWORD
  test.skip(
    !base || !staffBase || !username || !password,
    'Set Docker listener URLs and admin credentials',
  )
  await signIn(page, base!, username, password)
  await expect(page).toHaveURL(new URL('/teacher', staffBase!).toString())
  await expect(
    page.locator('form.account-form').filter({ hasText: 'Create teacher account' }),
  ).toBeVisible()
})

test('Docker student history and assigned teacher transcript work in the built app', async ({
  page,
}) => {
  const student = process.env.DEPLOYMENT_USERNAME
  const studentPassword = process.env.DEPLOYMENT_PASSWORD
  const teacher = process.env.DEPLOYMENT_TEACHER_USERNAME
  const teacherPassword = process.env.DEPLOYMENT_TEACHER_PASSWORD
  const base = process.env.DEPLOYMENT_URL
  const staffBase = process.env.DEPLOYMENT_STAFF_URL
  test.skip(
    !student || !studentPassword || !teacher || !teacherPassword || !base || !staffBase,
    'Set Docker URLs and QA student/teacher credentials',
  )

  await signIn(page, base!, student, studentPassword)
  await expect(page.getByRole('heading', { name: 'My learning' })).toBeVisible()
  const sessionsResponse = await page.request.get(`${base}/api/account/sessions`)
  expect(sessionsResponse.status()).toBe(200)
  const sessions = (await sessionsResponse.json()) as Array<{ id: string; title: string }>
  const moonSession = sessions.find((session) =>
    session.title.includes('Moon appears to change shape'),
  )
  expect(moonSession).toBeTruthy()
  const studentTranscriptResponse = await page.request.get(
    `${base}/api/account/sessions/${moonSession!.id}`,
  )
  expect(studentTranscriptResponse.status()).toBe(200)
  const studentTranscript = (await studentTranscriptResponse.json()) as {
    messages: Array<{ role: string; content: string }>
  }
  const studentAnswer = studentTranscript.messages
    .filter((message) => message.role === 'assistant')
    .at(-1)
  expect(studentAnswer).toBeTruthy()
  await page.getByRole('link', { name: 'View all sessions' }).click()
  const learnerSession = page
    .locator('.account-session')
    .filter({ has: page.getByRole('heading', { name: moonSession!.title, exact: true }) })
  await expect(learnerSession).toBeVisible()
  await learnerSession.getByRole('link', { name: 'Open session' }).click()
  await expect(page.locator('.message.user')).toContainText('Moon appears to change shape')
  const learnerAnswer = await page.locator('.message.assistant .message-content').last().innerText()
  expect(learnerAnswer.length).toBeGreaterThan(20)
  await page.getByRole('button', { name: 'Sign out' }).click()

  await signIn(page, staffBase!, teacher, teacherPassword)
  await expect(page.getByRole('heading', { name: 'Teacher dashboard' })).toBeVisible()
  await page.locator('.teacher-session-item').filter({ hasText: moonSession!.title }).click()
  await expect(page.locator('.teacher-transcript')).toContainText('Moon appears to change shape')
  expect(
    await page
      .locator('.teacher-transcript .message.assistant .message-content')
      .last()
      .textContent(),
  ).toBe(studentAnswer!.content)
})

test('Docker live AI chat persists and the assigned teacher can review it', async ({ page }) => {
  const student = process.env.DEPLOYMENT_USERNAME
  const studentPassword = process.env.DEPLOYMENT_PASSWORD
  const teacher = process.env.DEPLOYMENT_TEACHER_USERNAME
  const teacherPassword = process.env.DEPLOYMENT_TEACHER_PASSWORD
  const base = process.env.DEPLOYMENT_URL
  const staffBase = process.env.DEPLOYMENT_STAFF_URL
  test.skip(
    process.env.DEPLOYMENT_LIVE_AI !== '1' ||
      !student ||
      !studentPassword ||
      !teacher ||
      !teacherPassword ||
      !base ||
      !staffBase,
    'Set DEPLOYMENT_LIVE_AI=1 and Docker student/teacher credentials to call the live provider',
  )
  test.setTimeout(120_000)

  const question = `Docker live QA ${Date.now()}: explain how a push changes a ball's motion.`
  await signIn(page, base!, student, studentPassword)
  await page.goto(`${base}/tutor`)
  await page.getByLabel('Your question').fill(question)
  const chatResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/tutor/chat') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  const response = await chatResponse
  expect(response.status()).toBe(200)
  const reply = (await response.json()) as {
    answer: string
    model: string
    session_id: string
    grounding: string
  }
  expect(reply.answer.length).toBeGreaterThan(40)
  expect(reply.model.length).toBeGreaterThan(0)
  expect(reply.session_id).toMatch(/^[a-f0-9]{32}$/)
  await expect(page.locator('.message.assistant .message-content').last()).toBeVisible()
  const savedSession = await page.request.get(`${base}/api/account/sessions/${reply.session_id}`)
  expect(savedSession.status()).toBe(200)
  expect((await savedSession.json()).messages.at(-1).content).toBe(reply.answer)

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, staffBase!, teacher, teacherPassword)
  const sessionButton = page.locator('.teacher-session-item').filter({ hasText: question })
  await expect(sessionButton).toBeVisible()
  await sessionButton.click()
  await expect(page.locator('.teacher-transcript .message.user').last()).toContainText(question)
  expect(
    await page
      .locator('.teacher-transcript .message.assistant .message-content')
      .last()
      .textContent(),
  ).toBe(reply.answer)
})
