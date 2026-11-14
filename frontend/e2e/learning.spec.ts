import { expect, test, type Page } from '@playwright/test'

async function signIn(page: Page, username: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/auth/login') && response.request().method() === 'POST',
  )
  await page.locator('form.account-form').getByRole('button', { name: 'Sign in' }).first().click()
  expect((await loginResponse).status()).toBe(200)
  await expect(page).toHaveURL(username === 'e2e-student' ? '/dashboard' : '/teacher')
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  expect((await page.request.get('/api/auth/me')).status()).toBe(200)
}

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

test('courses page lists Kolibri channels with deep links', async ({ page }) => {
  await page.goto('/courses')
  await expect(page.getByRole('heading', { name: 'PhET Interactive Simulations' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Touchable Earth (en)' })).toBeVisible()
  await expect(page.getByText('Kolibri version 0.19.5')).toBeVisible()
  await expect(page.getByText('Listed only; content not imported yet')).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Open channel in Kolibri: Touchable Earth (en)' }),
  ).toHaveCount(0)
  await expect(
    page.getByRole('link', { name: 'Open channel in Kolibri: PhET Interactive Simulations' }),
  ).toHaveAttribute(
    'href',
    'http://kolibri.test:8080/en/learn/#/topics/c/197934f144305350b5820c7c4dd8e194',
  )
  await expect(page.getByRole('link', { name: 'Open the Kolibri library' })).toHaveAttribute(
    'href',
    'http://kolibri.test:8080',
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('staff import flows through the API, books open, and tutor shows real retrieval metadata', async ({
  page,
}) => {
  const project = test.info().project.name
  const bookTitle = `E2E force and motion ${project}`
  const subjectName = `Physics ${project}`
  const chapterName = `Force and Motion ${project}`
  await signIn(page, 'e2e-teacher', 'E2E-Teacher-Password-2026!')
  await page.goto('/staff')
  await expect(page.getByRole('heading', { name: 'Import a chapter' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Kolibri course management' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open Kolibri' })).toHaveAttribute(
    'href',
    'http://kolibri.test:8080',
  )
  await expect(page.getByRole('link', { name: 'Open Kolibri' })).toHaveAttribute('target', '_blank')
  await page.locator('details.kolibri-workflow > summary').click()
  await expect(page.locator('details.kolibri-workflow')).toHaveAttribute('open', '')
  await expect(
    page.getByRole('link', { name: 'Open the full Kolibri operations guide' }),
  ).toHaveAttribute('href', '/guides/kolibri.md')
  const guide = await page.request.get('/guides/kolibri.md')
  expect(guide.status()).toBe(200)
  expect(await guide.text()).toContain('Import a channel')
  await expect(page.getByText(/Review additions, changes, and removals/)).toBeVisible()
  await page.getByLabel('Document title').fill(bookTitle)
  await page.getByLabel('Subject', { exact: true }).fill(subjectName)
  await page.getByLabel('Chapter', { exact: true }).fill(chapterName)
  await page.getByLabel('License / permission').fill('CC0-1.0')
  await page.getByLabel('Source / attribution').fill('Original browser test fixture')
  await page.getByLabel('PDF or UTF-8 text file').setInputFiles({
    name: 'force.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('Newton’s second law: force equals mass times acceleration.'),
  })
  await page.getByRole('button', { name: 'Save to library' }).click()
  await expect(page.getByRole('status')).toHaveText(
    'Book saved. Index it below to enable tutor search.',
  )
  const savedBooks = await page.request.get('/api/textbooks?grade=8')
  const savedBook = (await savedBooks.json()).find(
    (book: { title: string }) => book.title === bookTitle,
  )
  expect(savedBook).toBeTruthy()
  await page.getByLabel('Book to index').selectOption(savedBook.id)
  await page.getByRole('button', { name: 'Index one book' }).click()
  await expect(page.locator('.index-library').getByRole('status')).toHaveText(
    'Book indexed. Its passages are available to tutor search.',
  )
  expect(
    await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length })),
  ).toEqual({ local: 0, session: 0 })
  await page.getByRole('link', { name: 'My textbooks', exact: true }).click()
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: bookTitle }),
  ).toBeVisible()
  const readerUrl = await page
    .getByRole('link', { name: `Open textbook: ${bookTitle}` })
    .getAttribute('href')
  expect(readerUrl).toMatch(/^\/books\/[a-f0-9]{32}$/)
  const bookId = readerUrl!.split('/').at(-1)
  const file = await page.request.get(`/api/textbooks/${bookId}/file`)
  expect(file.status()).toBe(200)
  expect(await file.text()).toContain('Newton')
  const tutorBooks = await page.request.get('/api/textbooks?grade=8')
  expect(tutorBooks.status()).toBe(200)
  expect(await tutorBooks.json()).toEqual(
    expect.arrayContaining([expect.objectContaining({ title: bookTitle, chapter: chapterName })]),
  )
  const tutorBooksLoaded = page.waitForResponse(
    (response) => response.url().includes('/api/textbooks?grade=8') && response.status() === 200,
  )
  await page.getByRole('link', { name: 'AI tutor', exact: true }).click()
  await tutorBooksLoaded
  const subject = page.getByLabel('Subject', { exact: true })
  await expect(subject).toHaveJSProperty('tagName', 'SELECT')
  await expect(subject.locator('option', { hasText: subjectName })).toHaveCount(1)
  await subject.selectOption(subjectName)
  await expect(subject).toHaveValue(subjectName)
  const chapter = page.getByLabel('Chapter', { exact: true })
  await expect(chapter.locator('option', { hasText: chapterName })).toHaveCount(1)
  await chapter.selectOption(chapterName)
  await page.getByLabel('Your question').fill('Explain force and mass.')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  await expect(page.getByText('Textbook passages retrieved', { exact: true })).toBeVisible()
  await expect(page.locator('.message.assistant .message-content strong')).toHaveText(
    'A force changes motion.',
  )
  await expect(page.locator('.message.assistant h3')).toHaveText('Example')
  await expect(page.getByRole('link', { name: `${bookTitle}, pages 1` })).toHaveAttribute(
    'href',
    /^\/books\/[a-f0-9]{32}\?page=1$/,
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
  await expect(page.locator('.message.user')).toContainText(
    'Explain force without a Grade 9 source.',
  )
  await expect(page.locator('.message.assistant')).toContainText('A force changes motion.')
})

test('student dashboard saves tutor history and assigned teacher can review the transcript', async ({
  page,
}) => {
  await signIn(page, 'e2e-student', 'E2E-Student-Password-2026!')
  await expect(page).toHaveURL('/dashboard')
  await expect(page.getByText('E2E Grade 8 A')).toBeVisible()
  await page.goto('/tutor')
  await page.getByLabel('Your question').fill('How does force change motion?')
  const chat = page.waitForResponse(
    (response) =>
      response.url().includes('/api/tutor/chat') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  const chatResponse = await chat
  expect(chatResponse.status()).toBe(200)
  const saved = await chatResponse.json()
  expect(saved.session_id).toMatch(/^[a-f0-9]{32}$/)
  await expect(page.locator('.message.assistant .message-content')).toContainText(
    'A force changes motion.',
  )

  await page.goto('/dashboard')
  await page.getByRole('link', { name: 'View all sessions' }).click()
  await expect(page.locator('.account-session h3')).toHaveText('How does force change motion?')
  await page.getByRole('link', { name: 'Open session' }).click()
  await expect(page.locator('.message.user')).toContainText('How does force change motion?')
  await expect(page.locator('.message.assistant')).toContainText('A force changes motion.')

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, 'e2e-teacher', 'E2E-Teacher-Password-2026!')
  await expect(page).toHaveURL('/teacher')
  await expect(page.getByRole('combobox', { name: 'Assigned classes' })).toContainText(
    'E2E Grade 8 A',
  )
  await page.getByRole('button', { name: /E2E Student/ }).click()
  await expect(page.locator('.teacher-transcript')).toContainText('How does force change motion?')
  await expect(page.locator('.teacher-transcript')).toContainText('A force changes motion.')

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, 'e2e-student', 'E2E-Student-Password-2026!')
  await page.goto('/history')
  await expect(page.getByRole('link', { name: 'Open session' })).toHaveCount(1)
  await page.getByRole('button', { name: 'Delete session' }).click()
  await expect(page.getByText('Your saved tutor sessions will appear here.')).toBeVisible()
})

test('administrator can create, reset, disable, and restore named accounts', async ({ page }) => {
  await signIn(page, 'e2e-admin', 'E2E-Admin-Password-2026!')
  await expect(page).toHaveURL('/teacher')
  const createdUsername = `e2e-created-${Date.now()}`
  const teacherForm = page
    .locator('form.account-form')
    .filter({ hasText: 'Create teacher account' })
  await teacherForm.getByLabel('Name shown in school').fill('New E2E Teacher')
  await teacherForm.getByLabel('Username').fill(createdUsername)
  await teacherForm.getByLabel('Password').fill('E2E-Created-Teacher-2026!')
  await teacherForm.getByRole('button', { name: 'Create teacher account' }).click()
  await expect(page.locator('.learner-list li').filter({ hasText: createdUsername })).toBeVisible()
  await page.getByLabel('Filter accounts').fill(createdUsername)
  const accountRow = page.locator('.learner-list li').filter({ hasText: createdUsername })
  await expect(accountRow).toBeVisible()
  await accountRow.getByRole('button', { name: 'Reset password' }).click()
  await expect(accountRow.locator('.temporary-credential')).toContainText('Temp-')
  await accountRow.getByRole('button', { name: 'Deactivate' }).click()
  await expect(accountRow).toContainText('Account disabled')
  await accountRow.getByRole('button', { name: 'Restore' }).click()
  await expect(accountRow).toContainText('Must change initial password')
})

test('textbook filters include Kindergarten and cross-grade resources', async ({ page }) => {
  const books = [
    {
      id: 'a'.repeat(32),
      title: 'Early childhood curriculum',
      grade: 0,
      subject: 'Early Childhood Education',
      chapter: 'Whole book',
      license: 'User-confirmed local prototype permission',
      source: 'https://moecdc.gov.np/content/671/early-childhood-curriculum/',
      pages: 1,
      status: 'ready',
      ocr_required_pages: [],
    },
    {
      id: 'b'.repeat(32),
      title: 'Basic level reference material',
      grade: null,
      subject: 'General Learning Resources',
      chapter: 'Whole book',
      license: 'User-confirmed local prototype permission',
      source: 'https://moecdc.gov.np/content/373/basic-level-reference/',
      pages: 1,
      status: 'ready',
      ocr_required_pages: [],
    },
  ]
  await page.route('**/api/textbooks/catalog*', (route) => {
    const url = new URL(route.request().url())
    const grade = url.searchParams.get('grade')
    const subject = url.searchParams.get('subject')
    const query = url.searchParams.get('q')?.toLowerCase() ?? ''
    const offset = Number(url.searchParams.get('offset') ?? 0)
    const limit = Number(url.searchParams.get('limit') ?? 24)
    const visible =
      grade === null
        ? books
        : books.filter((book) => book.grade === null || book.grade === Number(grade))
    const filtered = visible.filter(
      (book) =>
        (!subject || book.subject === subject) &&
        (!query || `${book.title} ${book.subject} ${book.chapter}`.toLowerCase().includes(query)),
    )
    return route.fulfill({
      json: {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        limit,
        offset,
        subjects: [...new Set(visible.map((book) => book.subject))],
      },
    })
  })
  await page.goto('/books')

  const grade = page.getByLabel('Grade', { exact: true })
  await expect(grade.locator('option[value=""]')).toHaveText('All grades')
  await expect(grade.locator('option[value="0"]')).toHaveText('Kindergarten (K)')
  await grade.selectOption('')
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Early childhood curriculum' }),
  ).toBeVisible()
  await expect(
    page
      .locator('.catalog-results')
      .getByRole('heading', { name: 'Basic level reference material' }),
  ).toBeVisible()
  await expect(page.locator('.book-preview, .preview-document')).toHaveCount(0)
  await page.getByRole('checkbox', { name: 'Select book: Early childhood curriculum' }).check()
  await expect(page.locator('.catalog-toolbar .selection-count')).toContainText('1 selected')
  await expect(page.locator('.book-preview, .preview-document')).toHaveCount(0)
  await grade.selectOption('0')
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Early childhood curriculum' }),
  ).toBeVisible()
  await expect(
    page
      .locator('.catalog-results')
      .getByRole('heading', { name: 'Basic level reference material' }),
  ).toBeVisible()
})

test('textbook catalog searches, selects, and paginates without a default preview', async ({
  page,
}) => {
  const books = Array.from({ length: 25 }, (_, index) => ({
    id: String(index + 1).padStart(32, '0'),
    title: `Grade ${index + 1} ${index % 2 ? 'Mathematics' : 'Science'}`,
    grade: (index % 12) + 1,
    subject: index % 2 ? 'Mathematics' : 'Science',
    chapter: `Chapter ${index + 1}`,
    license: 'Prototype test fixture',
    source: 'Local test fixture',
    pages: 8,
    status: 'ready',
    chunks: 0,
    index_status: 'not_indexed',
    ocr_required_pages: [],
  }))
  await page.route('**/api/textbooks/catalog*', (route) => {
    const url = new URL(route.request().url())
    const query = url.searchParams.get('q')?.toLowerCase() ?? ''
    const subject = url.searchParams.get('subject') ?? ''
    const grade = url.searchParams.get('grade')
    const offset = Number(url.searchParams.get('offset') ?? 0)
    const limit = Number(url.searchParams.get('limit') ?? 24)
    const filtered = books.filter(
      (book) =>
        (!query || `${book.title} ${book.subject} ${book.chapter}`.toLowerCase().includes(query)) &&
        (!subject || book.subject === subject) &&
        (!grade || book.grade === Number(grade)),
    )
    return route.fulfill({
      json: {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        limit,
        offset,
        subjects: [...new Set(books.map((book) => book.subject))],
      },
    })
  })
  await page.goto('/books')
  await expect(page.locator('.book-preview, .preview-document')).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.locator('.catalog-count')).toContainText('Showing 1–24 of 25 books')
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Grade 1 Science' }),
  ).toBeVisible()
  await page.getByRole('checkbox', { name: 'Select book: Grade 1 Science' }).check()
  await expect(page.locator('.catalog-toolbar .selection-count')).toContainText('1 selected')
  await expect(page.locator('.book-preview, .preview-document')).toHaveCount(0)
  await expect(page).toHaveURL(/\/books$/)
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.locator('.catalog-count')).toContainText('Showing 25–25 of 25 books')
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Grade 25 Science' }),
  ).toBeVisible()
  await page.getByLabel('Search books').fill('mathematics')
  await expect(page.locator('.catalog-count')).toContainText('of 12 books')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Grade 1 Science' }),
  ).toHaveCount(0)
})

test('clicking a textbook opens its in-app reader and keeps text readable', async ({ page }) => {
  const book = {
    id: 'c'.repeat(32),
    title: 'Early childhood curriculum',
    filename: 'early-childhood.txt',
    grade: 0,
    subject: 'Early Childhood Education',
    chapter: 'Whole book',
    license: 'Prototype test fixture',
    source: 'Local test fixture',
    pages: 4,
    status: 'ready',
    chunks: 0,
    index_status: 'not_indexed',
    ocr_required_pages: [],
  }
  await page.route('**/api/textbooks/catalog*', (route) =>
    route.fulfill({
      json: { items: [book], total: 1, limit: 24, offset: 0, subjects: [book.subject] },
    }),
  )
  await page.route(`**/api/textbooks/${book.id}`, (route) => route.fulfill({ json: book }))
  await page.route(`**/api/textbooks/${book.id}/file`, (route) =>
    route.fulfill({
      contentType: 'text/plain',
      body: 'Learning begins with curiosity.\n\nRead together.',
    }),
  )

  await page.goto('/books')
  await expect(page.locator('.reader-document, .book-preview, .preview-document')).toHaveCount(0)
  await page.getByRole('link', { name: 'Open textbook: Early childhood curriculum' }).click()
  await expect(page).toHaveURL(`/books/${book.id}`)
  await expect(page.locator('.reader-heading h1')).toHaveText(book.title)
  await expect(page.locator('.reader-document')).toBeVisible()
  await expect(page.getByText('Grade K · Early Childhood Education')).toBeVisible()
  await expect(page.locator('.reader-text pre')).toContainText('Learning begins with curiosity.')
  await expect(page.getByRole('link', { name: 'Back to textbooks' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open original file in a new tab' })).toHaveAttribute(
    'target',
    '_blank',
  )
  if ((page.viewportSize()?.width ?? 0) <= 640) {
    await expect(page.locator('.reader-back-short')).toBeVisible()
    await expect(page.locator('.reader-back-full')).not.toBeVisible()
    await expect(page.locator('.reader-original-label')).not.toBeVisible()
    await expect(page.locator('.reader-page-count')).not.toBeVisible()
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)

  await page.getByRole('link', { name: 'Back to textbooks' }).click()
  await expect(page).toHaveURL('/books')
})

test('PDF textbooks open in a large embedded viewer', async ({ page }) => {
  const book = {
    id: 'd'.repeat(32),
    title: 'Grade 9 Science',
    filename: 'grade-9-science.pdf',
    grade: 9,
    subject: 'Science',
    chapter: 'Whole book',
    license: 'Prototype test fixture',
    source: 'Local test fixture',
    pages: 41,
    status: 'ready',
    chunks: 0,
    index_status: 'not_indexed',
    ocr_required_pages: [],
  }
  await page.route(`**/api/textbooks/${book.id}`, (route) => route.fulfill({ json: book }))
  await page.route(`**/api/textbooks/${book.id}/file`, (route) =>
    route.fulfill({ contentType: 'application/pdf', body: '%PDF-1.4\n%EOF' }),
  )

  await page.goto(`/books/${book.id}`)
  const reader = page.getByTitle(`Book content: ${book.title}`)
  await expect(reader).toBeVisible()
  await expect(reader).toHaveAttribute(
    'src',
    new RegExp(`/api/textbooks/${book.id}/file#toolbar=1`),
  )
  expect(await reader.evaluate((frame) => frame.clientHeight)).toBeGreaterThan(350)
  await expect(page.getByText('41 pages', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
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

test('primary navigation is a full-width sticky navbar at desktop, tablet, and phone sizes', async ({
  page,
}) => {
  for (const width of [1280, 663, 390]) {
    await page.setViewportSize({ width, height: 857 })
    await page.goto('/')

    const navbar = page.locator('.topbar')
    const navigation = page.getByRole('navigation', { name: 'Main navigation' })
    await expect(page.locator('.sidebar')).toHaveCount(0)
    await expect(navbar).toHaveCSS('position', 'sticky')
    await expect(navbar).toHaveCSS('width', `${width}px`)
    await expect(navbar.locator('.connection, .language-toggle, .topbar-brand')).toHaveCount(0)
    await expect(navigation.getByRole('link')).toHaveCount(6)
    await expect(navigation.getByRole('link', { name: 'Learning home' })).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'AI tutor' })).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'My textbooks' })).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'Study notes' })).toBeVisible()
    await expect(navigation.getByRole('link', { name: 'Courses' })).toBeVisible()
    await expect(page.locator('.footer-brand')).toContainText('Himalaya')
    await expect(page.locator('.footer-meta .connection')).toBeVisible()
    await expect(page.locator('.footer-meta .language-toggle')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)

    if (width === 390) {
      await expect(navigation.locator('.nav-label-short')).toHaveCount(6)
      await expect(navigation.locator('.nav-label-short').first()).toBeVisible()
      await expect(navigation.locator('.nav-label-full').first()).toBeHidden()
    }

    await page.evaluate(() => window.scrollTo({ top: 1000, behavior: 'instant' }))
    await expect
      .poll(() => navbar.evaluate((node) => Math.round(node.getBoundingClientRect().top)))
      .toBe(0)

    await navigation.getByRole('link', { name: 'My textbooks' }).click()
    await expect(page.getByRole('heading', { name: 'My textbooks' })).toBeVisible()
  }
})

test('approved teacher note appears in study notes, tutor modes, and reader pages', async ({
  page,
}, testInfo) => {
  // The API fixture is shared by both browser projects, so each run uses its own names.
  const tag = testInfo.project.name
  const subject = `Chemistry ${tag}`
  const title = `Parts of an atom ${tag}`
  await signIn(page, 'e2e-teacher', 'E2E-Teacher-Password-2026!')
  const authResponse = await page.request.get('/api/auth/me')
  expect(authResponse.status()).toBe(200)
  const headers = { 'X-CSRF-Token': (await authResponse.json()).csrf_token as string }
  const imported = await page.request.post('/api/admin/documents', {
    headers,
    multipart: {
      title: `E2E atoms book ${tag}`,
      grade: '8',
      subject,
      chapter: 'Atoms',
      license: 'CC0-1.0',
      source: 'Original browser test fixture',
      file: {
        name: 'atoms.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Atoms contain protons, neutrons and electrons.'),
      },
    },
  })
  expect(imported.status()).toBe(201)
  const book = await imported.json()
  const created = await page.request.post('/api/admin/notes', {
    headers,
    data: {
      title,
      grade: 8,
      subject,
      chapter: 'Atoms',
      language: 'en',
      document_id: book.id,
      pages: [{ start: 1, end: 1 }],
      key_ideas: ['Atoms contain protons, neutrons and electrons.'],
      worked_example: 'Carbon has 6 protons.',
      misconceptions: [{ wrong: 'Electrons are in the nucleus.', correction: 'They orbit it.' }],
      hints: ['Name the particles first.', `Which particle has a negative charge? (${tag})`],
      check_question: `Which particle is negative? (${tag})`,
    },
  })
  expect(created.status()).toBe(201)
  const note = await created.json()
  await page.goto('/study')
  await expect(page.getByRole('heading', { name: title })).toHaveCount(0)
  const review = (status: string, reviewer = '') =>
    page.request.post(`/api/admin/notes/${note.id}/review`, {
      headers,
      data: { status, reviewer },
    })
  expect((await review('in_review')).status()).toBe(200)
  await page.goto('/staff')
  const reviewRow = page.locator('.staff-note-list li').filter({ hasText: title })
  await expect(reviewRow.getByRole('button', { name: 'Approve' })).toHaveCount(0)
  await expect(reviewRow).toContainText(
    'A different teacher or administrator must approve this note.',
  )
  const browser = page.context().browser()
  expect(browser).not.toBeNull()
  const adminContext = await browser!.newContext({ baseURL: new URL(page.url()).origin })
  const adminLogin = await adminContext.request.post('/api/auth/login', {
    data: { username: 'e2e-admin', password: 'E2E-Admin-Password-2026!' },
  })
  expect(adminLogin.status()).toBe(200)
  const adminHeaders = { 'X-CSRF-Token': (await adminLogin.json()).csrf_token as string }
  const approval = await adminContext.request.post(`/api/admin/notes/${note.id}/review`, {
    headers: adminHeaders,
    data: { status: 'approved' },
  })
  expect(approval.status()).toBe(200)
  await adminContext.close()

  await page.goto('/study')
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
  const card = page.locator('article.study-note', { hasText: title })
  await expect(card.getByText(`Which particle is negative? (${tag})`)).toBeVisible()
  const second = card.getByText(`Which particle has a negative charge? (${tag})`)
  await expect(second).toHaveCount(0)
  await card.getByRole('button', { name: 'Show the next hint' }).click()
  await card.getByRole('button', { name: 'Show the next hint' }).click()
  await expect(second).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await card.getByRole('link', { name: 'Open book at page 1' }).click()
  await expect(page.getByText(/Opened at page 1/)).toBeVisible()

  await page.goto('/tutor')
  await page.getByLabel('Subject', { exact: true }).selectOption(subject)
  await page.getByRole('radio', { name: /Check my work/ }).check()
  await page.getByLabel('Your question').fill('Check my atoms and protons answer.')
  await expect(page.getByRole('button', { name: 'Check my work' }).last()).toBeDisabled()
  await page.getByLabel('Your attempt').fill('Electrons are in the nucleus')
  await page.getByRole('button', { name: 'Check my work' }).last().click()
  await expect(page.getByText('Reviewed teacher note supplied')).toBeVisible()
  await expect(
    page.getByRole('link', { name: new RegExp(`Teacher note: ${title}, pages 1`) }),
  ).toHaveAttribute('href', `/books/${book.id}?page=1`)
  await page.getByRole('radio', { name: /Hint/ }).check()
  await expect(page.getByText('Hint 1 / 5')).toBeVisible()
})
