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
  await expect(page.getByRole('heading', { name: 'Kolibri course management' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open Kolibri' })).toHaveAttribute(
    'href',
    'http://kolibri.test:8080',
  )
  await expect(page.getByRole('link', { name: 'Open Kolibri' })).toHaveAttribute('target', '_blank')
  await page.getByText('Channel import and update workflow').click()
  await expect(page.getByText(/Review additions, changes, and removals/)).toBeVisible()
  await page.getByLabel('Document title').fill('E2E force and motion')
  await page.getByLabel('Subject', { exact: true }).fill('Physics')
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
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'E2E force and motion' }),
  ).toBeVisible()
  const readerUrl = await page
    .getByRole('link', { name: 'Open textbook', exact: true })
    .getAttribute('href')
  expect(readerUrl).toMatch(/^\/books\/[a-f0-9]{32}$/)
  const bookId = readerUrl!.split('/').at(-1)
  const file = await page.request.get(`/api/textbooks/${bookId}/file`)
  expect(file.status()).toBe(200)
  expect(await file.text()).toContain('Newton')
  const tutorBooks = await page.request.get('/api/textbooks?grade=8')
  expect(tutorBooks.status()).toBe(200)
  expect(await tutorBooks.json()).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ title: 'E2E force and motion', chapter: 'Force and Motion' }),
    ]),
  )
  const tutorBooksLoaded = page.waitForResponse(
    (response) => response.url().includes('/api/textbooks?grade=8') && response.status() === 200,
  )
  await page.getByRole('link', { name: 'AI tutor', exact: true }).click()
  await tutorBooksLoaded
  const subject = page.getByLabel('Subject', { exact: true })
  await expect(subject).toHaveJSProperty('tagName', 'SELECT')
  await expect(subject.locator('option', { hasText: 'Physics' })).toHaveCount(1)
  await subject.selectOption('Physics')
  await expect(subject).toHaveValue('Physics')
  const chapter = page.getByLabel('Chapter', { exact: true })
  await expect(chapter.locator('option', { hasText: 'Force and Motion' })).toHaveCount(1)
  await chapter.selectOption('Force and Motion')
  await page.getByLabel('Your question').fill('Explain force and mass.')
  await page.getByRole('button', { name: 'Ask the tutor' }).click()
  await expect(page.getByText('Textbook passages retrieved', { exact: true })).toBeVisible()
  await expect(page.locator('.message.assistant .message-content strong')).toHaveText(
    'A force changes motion.',
  )
  await expect(page.locator('.message.assistant h3')).toHaveText('Example')
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
  await expect(page.getByTitle('Preview: Early childhood curriculum')).toBeVisible()
  await page.getByRole('checkbox', { name: 'Select book: Early childhood curriculum' }).check()
  await expect(page.locator('.catalog-toolbar .selection-count')).toContainText('1 selected')
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

test('textbook catalog searches, previews, selects, and paginates', async ({ page }) => {
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
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await expect(page.locator('.catalog-count')).toContainText('Showing 1–24 of 25 books')
  await expect(
    page.locator('.catalog-results').getByRole('heading', { name: 'Grade 1 Science' }),
  ).toBeVisible()
  await page.getByRole('checkbox', { name: 'Select book: Grade 1 Science' }).check()
  await expect(page.locator('.catalog-toolbar .selection-count')).toContainText('1 selected')
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
  await page.getByRole('link', { name: 'Open textbook: Early childhood curriculum' }).click()
  await expect(page).toHaveURL(`/books/${book.id}`)
  await expect(page.locator('.reader-heading h1')).toHaveText(book.title)
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

test('desktop sidebar collapses to an icon rail and remembers the choice', async ({ page }) => {
  await page.goto('/tutor')
  const sidebar = page.locator('.sidebar')
  const shell = page.locator('.app-shell')
  const toggle = page.locator('.sidebar-toggle')
  const width = page.viewportSize()?.width ?? 0

  if (width <= 640) {
    await expect(toggle).not.toBeVisible()
    await expect(page.locator('.sidebar-head')).not.toBeVisible()
    await expect(sidebar.getByRole('navigation').getByRole('link')).toHaveCount(3)
    await expect(page.locator('.footer-brand')).toContainText('Digital Himalaya')
    await expect(page.locator('.footer-brand img')).toBeVisible()
    await expect(sidebar.getByRole('link', { name: 'AI tutor' })).toBeVisible()
    return
  }

  await expect(page.locator('.brand-label')).toHaveText('Himalaya')
  await expect(page.locator('.footer-brand')).toContainText('Digital Himalaya')
  await expect(page.locator('.sidebar .brand img')).toHaveCount(0)
  await expect(page.locator('.footer-brand img')).toBeVisible()
  await expect(toggle).toHaveAccessibleName('Collapse sidebar')
  await expect(toggle).toHaveAttribute('aria-pressed', 'false')
  await expect(sidebar).toHaveCSS('width', width <= 850 ? '190px' : '226px')
  await toggle.click()
  await expect(toggle).toHaveAccessibleName('Expand sidebar')
  await expect(toggle).toHaveAttribute('aria-pressed', 'true')
  await expect(sidebar).toHaveCSS('width', '92px')
  await expect(page.locator('.sidebar-head')).toHaveCSS('margin-bottom', '16px')
  await expect(sidebar.getByRole('navigation')).toHaveCSS('row-gap', '4px')
  await expect(sidebar.getByRole('link', { name: 'AI tutor' })).toHaveCSS('min-height', '44px')
  await expect(page.locator('.workspace')).toHaveCSS('margin-left', '92px')
  await expect(sidebar.getByRole('link', { name: 'AI tutor' })).toHaveAttribute('title', 'AI tutor')
  await expect(page.getByRole('heading', { name: 'AI tutor' })).toBeVisible()

  await page.reload()
  await expect(shell).toHaveClass(/is-sidebar-collapsed/)
  await expect(toggle).toHaveAccessibleName('Expand sidebar')
  await toggle.click()
  await expect(toggle).toHaveAccessibleName('Collapse sidebar')
  await expect(sidebar).toHaveCSS('width', width <= 850 ? '190px' : '226px')

  if (width > 850) {
    await page.setViewportSize({ width: 800, height: 900 })
    await expect(sidebar).toHaveCSS('width', '190px')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

test('mobile navigation stays available while scrolling', async ({ page }) => {
  test.skip((page.viewportSize()?.width ?? 0) > 640, 'The desktop navigation uses a fixed sidebar.')
  await page.goto('/')
  await expect(page.locator('.sidebar-head')).not.toBeVisible()
  await expect(page.getByRole('navigation').getByRole('link')).toHaveCount(3)
  await expect(page.locator('.footer-brand')).toContainText('Digital Himalaya')
  await expect(page.locator('.footer-brand img')).toBeVisible()
  await page.evaluate(() => window.scrollTo({ top: 1000, behavior: 'instant' }))
  await expect
    .poll(() =>
      page.locator('.sidebar').evaluate((nav) => Math.round(nav.getBoundingClientRect().top)),
    )
    .toBe(0)
  await page
    .getByRole('navigation')
    .getByRole('link', { name: 'My textbooks', exact: true })
    .click()
  await expect(page.getByRole('heading', { name: 'My textbooks' })).toBeVisible()
})
