import { useEffect, useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  CaretLeft,
  CaretRight,
  MagnifyingGlass,
  X,
} from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { api, type Book, type TextbookCatalog } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

const PAGE_SIZES = [12, 24, 48]
const EMPTY_BOOKS: Book[] = []

function bookGrade(book: Book, t: Copy) {
  return book.grade === null ? t.allGrades : `${t.grade} ${book.grade === 0 ? 'K' : book.grade}`
}

function indexState(book: Book) {
  return book.index_status ?? ((book.chunks ?? 0) > 0 ? 'indexed' : 'not_indexed')
}

export default function Books({ t }: { t: Copy }) {
  const [catalog, setCatalog] = useState<TextbookCatalog | null>(null)
  const [grade, setGrade] = useState('')
  const [subject, setSubject] = useState('')
  const [query, setQuery] = useState('')
  const [pageSize, setPageSize] = useState(24)
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<Record<string, Book>>({})
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => {
      setLoading(true)
      setError(null)
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      })
      if (grade) params.set('grade', grade)
      if (subject) params.set('subject', subject)
      if (query.trim()) params.set('q', query.trim())
      api<TextbookCatalog>(`/textbooks/catalog?${params.toString()}`, { signal: controller.signal })
        .then((data) => {
          setCatalog(data)
          if (page > 0 && page * pageSize >= data.total) {
            setPage(Math.max(0, Math.ceil(data.total / pageSize) - 1))
          }
        })
        .catch((e) => {
          if (!controller.signal.aborted) setError(e)
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false)
        })
    }, 180)
    return () => {
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [grade, subject, query, page, pageSize, attempt])

  const books = catalog?.items ?? EMPTY_BOOKS
  const selectedBooks = Object.values(selected)
  const firstResult = catalog && catalog.total ? catalog.offset + 1 : 0
  const lastResult = catalog ? Math.min(catalog.offset + catalog.items.length, catalog.total) : 0
  const pageCount = catalog ? Math.max(1, Math.ceil(catalog.total / pageSize)) : 1
  const allOnPageSelected = books.length > 0 && books.every((book) => selected[book.id])

  function updateGrade(value: string) {
    setGrade(value)
    setSubject('')
    setPage(0)
  }

  function updateSubject(value: string) {
    setSubject(value)
    setPage(0)
  }

  function toggleBook(book: Book) {
    const next = { ...selected }
    if (next[book.id]) {
      delete next[book.id]
    } else {
      next[book.id] = book
    }
    setSelected(next)
  }

  function togglePageSelection() {
    const next = { ...selected }
    if (allOnPageSelected) books.forEach((book) => delete next[book.id])
    else books.forEach((book) => (next[book.id] = book))
    setSelected(next)
  }

  function clearSelection() {
    setSelected({})
  }

  return (
    <>
      <header className="page-heading">
        <h1>{t.books}</h1>
        <p>{t.booksDescription}</p>
      </header>

      <section className="catalog-tools" aria-label={t.bookFilters}>
        <div className="catalog-search">
          <MagnifyingGlass size={20} aria-hidden="true" />
          <input
            aria-label={t.searchBooks}
            placeholder={t.searchBooksHint}
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setPage(0)
            }}
          />
        </div>
        <div className="catalog-selects">
          <Field label={t.grade}>
            <select value={grade} onChange={(event) => updateGrade(event.target.value)}>
              <option value="">{t.allGrades}</option>
              <option value="0">{t.kindergarten}</option>
              {Array.from({ length: 12 }, (_, index) => (
                <option key={index + 1} value={index + 1}>
                  {index + 1}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t.subject}>
            <select value={subject} onChange={(event) => updateSubject(event.target.value)}>
              <option value="">{t.allSubjects}</option>
              {(catalog?.subjects ?? []).map((name) => (
                <option value={name} key={name}>
                  {name}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </section>

      <div className="catalog-toolbar">
        <div className="catalog-count" aria-live="polite">
          {loading && !catalog ? (
            t.loading
          ) : (
            <>
              {t.showing}{' '}
              <strong>
                {firstResult}–{lastResult}
              </strong>{' '}
              {t.of} <strong>{catalog?.total ?? 0}</strong> {t.booksLabel}
            </>
          )}
        </div>
        <div className="catalog-actions">
          <button className="text-button" onClick={togglePageSelection} disabled={!books.length}>
            {allOnPageSelected ? t.clearPageSelection : t.selectPage}
          </button>
          {selectedBooks.length > 0 && (
            <span className="selection-count">
              {selectedBooks.length} {t.selected}
              <button
                className="icon-button"
                aria-label={t.clearSelection}
                onClick={clearSelection}
              >
                <X size={17} aria-hidden="true" />
              </button>
            </span>
          )}
        </div>
      </div>

      <ErrorNotice error={error} t={t} />
      {error ? (
        <button className="secondary" onClick={() => setAttempt((value) => value + 1)}>
          {t.retry}
        </button>
      ) : loading && !catalog ? (
        <div className="catalog-loading" role="status">
          <span />
          <span />
          <span />
          <span />
        </div>
      ) : !books.length ? (
        <div className="empty-state">
          <BookOpen size={45} aria-hidden="true" />
          <h2>{catalog?.total ? t.noMatches : t.noBooks}</h2>
          <p>{catalog?.total ? t.noMatchesNote : t.noBooksNote}</p>
        </div>
      ) : (
        <div className="catalog-layout">
          <section className="catalog-results" aria-label={t.bookResults}>
            {books.map((book) => {
              const isSelected = Boolean(selected[book.id])
              const status = indexState(book)
              return (
                <article
                  className={`catalog-book${isSelected ? ' is-selected' : ''}`}
                  key={book.id}
                >
                  <label className="book-check" aria-label={`${t.selectBook}: ${book.title}`}>
                    <input type="checkbox" checked={isSelected} onChange={() => toggleBook(book)} />
                    <span aria-hidden="true" />
                  </label>
                  <Link
                    className="catalog-book-main"
                    to={`/books/${book.id}`}
                    aria-label={`${t.openBook}: ${book.title}`}
                  >
                    <span className="catalog-book-icon">
                      <BookOpen size={21} aria-hidden="true" />
                    </span>
                    <span className="catalog-book-copy">
                      <span className="catalog-book-meta">
                        {bookGrade(book, t)} <span aria-hidden="true">·</span> {book.subject}
                      </span>
                      <span className="catalog-book-title" role="heading" aria-level={2}>
                        {book.title}
                      </span>
                      <span className="catalog-book-subtitle">
                        {book.chapter} <span aria-hidden="true">·</span> {book.pages} {t.pages}
                      </span>
                    </span>
                    <ArrowRight className="catalog-book-arrow" size={18} aria-hidden="true" />
                  </Link>
                  <span className={`index-status index-${status}`}>
                    {t[status as keyof Copy] ?? t.notIndexed}
                  </span>
                </article>
              )
            })}

            <nav className="catalog-pagination" aria-label={t.bookPagination}>
              <label className="page-size-label">
                <span>{t.perPage}</span>
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value))
                    setPage(0)
                  }}
                  aria-label={t.perPage}
                >
                  {PAGE_SIZES.map((size) => (
                    <option value={size} key={size}>
                      {size}
                    </option>
                  ))}
                </select>
              </label>
              <span className="page-indicator">
                {t.page} {page + 1} {t.of} {pageCount}
              </span>
              <div className="page-buttons">
                <button
                  className="icon-button"
                  aria-label={t.previousPage}
                  disabled={page === 0 || loading}
                  onClick={() => setPage((value) => Math.max(0, value - 1))}
                >
                  <CaretLeft size={19} aria-hidden="true" />
                </button>
                <button
                  className="icon-button"
                  aria-label={t.nextPage}
                  disabled={page + 1 >= pageCount || loading}
                  onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}
                >
                  <CaretRight size={19} aria-hidden="true" />
                </button>
              </div>
            </nav>
          </section>
        </div>
      )}
    </>
  )
}
