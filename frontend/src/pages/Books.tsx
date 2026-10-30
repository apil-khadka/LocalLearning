import { useEffect, useState } from 'react'
import { BookOpen, ArrowSquareOut } from '@phosphor-icons/react'
import { api, type Book } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

export default function Books({ t }: { t: Copy }) {
  const [books, setBooks] = useState<Book[]>([])
  const [grade, setGrade] = useState('8')
  const [subject, setSubject] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    api<Book[]>(`/textbooks?grade=${grade}`, { signal: controller.signal })
      .then(setBooks)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [grade, attempt])
  const filtered = books.filter((book) =>
    book.subject.toLowerCase().includes(subject.trim().toLowerCase()),
  )
  return (
    <>
      <header className="page-heading">
        <h1>{t.books}</h1>
        <p>{t.booksDescription}</p>
      </header>
      <div className="filter-row">
        <Field label={t.grade}>
          <select value={grade} onChange={(e) => setGrade(e.target.value)}>
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i} value={i + 1}>
                {i + 1}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t.subject}>
          <input value={subject} onChange={(e) => setSubject(e.target.value)} type="search" />
        </Field>
      </div>
      <ErrorNotice error={error} t={t} />
      {error ? (
        <button onClick={() => setAttempt((x) => x + 1)}>{t.retry}</button>
      ) : loading ? (
        <p role="status">{t.loading}</p>
      ) : !filtered.length ? (
        <div className="empty-state">
          <BookOpen size={45} aria-hidden="true" />
          <h2>{t.noBooks}</h2>
          <p>{t.noBooksNote}</p>
        </div>
      ) : (
        <div className="book-list">
          {filtered.map((book) => (
            <article className="book" key={book.id}>
              <span className="resource-icon green">
                <BookOpen size={26} aria-hidden="true" />
              </span>
              <div>
                <p className="muted">
                  {t.grade} {book.grade} / {book.subject}
                </p>
                <h2>{book.title}</h2>
                <p>
                  {book.chapter} / {book.pages} {t.pages}
                </p>
                <small>
                  {book.license} / {book.source}
                </small>
                {book.ocr_required_pages.length > 0 && (
                  <p className="notice">
                    {t.ocr}: {book.ocr_required_pages.join(', ')}
                  </p>
                )}
              </div>
              <a
                className="button secondary"
                href={`/api/textbooks/${book.id}/file`}
                target="_blank"
                rel="noreferrer"
              >
                {t.openBook}
                <ArrowSquareOut size={18} aria-hidden="true" />
              </a>
            </article>
          ))}
        </div>
      )}
    </>
  )
}
