import { useEffect, useState } from 'react'
import { ArrowLeft, ArrowSquareOut, BookOpen } from '@phosphor-icons/react'
import { Link, useParams } from 'react-router-dom'
import { api, type Book } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice } from '../components/ui'

function gradeLabel(book: Book, t: Copy) {
  return book.grade === null ? t.allGrades : `${t.grade} ${book.grade === 0 ? 'K' : book.grade}`
}

export default function BookReader({ t }: { t: Copy }) {
  const { id = '' } = useParams()
  const [book, setBook] = useState<Book | null>(null)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [attempt, setAttempt] = useState(0)
  const isTextFile = Boolean(book?.filename && !book.filename.toLowerCase().endsWith('.pdf'))

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setBook(null)
    setText('')

    api<Book>(`/textbooks/${id}`, { signal: controller.signal })
      .then(async (document) => {
        setBook(document)
        if (!document.filename || document.filename.toLowerCase().endsWith('.pdf')) return
        const response = await fetch(`/api/textbooks/${id}/file`, { signal: controller.signal })
        if (!response.ok) throw new Error('The textbook file could not be loaded.')
        setText(await response.text())
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [id, attempt])

  return (
    <section className="book-reader">
      <div className="reader-navigation">
        <Link className="button secondary reader-back" to="/books">
          <ArrowLeft size={18} aria-hidden="true" />
          {t.backToBooks}
        </Link>
        {book && (
          <a
            className="reader-original-link"
            href={`/api/textbooks/${book.id}/file`}
            target="_blank"
            rel="noreferrer"
          >
            {t.openOriginalFile}
            <ArrowSquareOut size={17} aria-hidden="true" />
          </a>
        )}
      </div>

      {loading ? (
        <div className="catalog-loading reader-loading" role="status">
          <span />
        </div>
      ) : error || !book ? (
        <div className="reader-error">
          <ErrorNotice error={error ?? new Error(t.notFound)} t={t} />
          <button className="secondary" onClick={() => setAttempt((value) => value + 1)}>
            {t.retry}
          </button>
        </div>
      ) : (
        <>
          <header className="reader-heading">
            <div className="reader-book-icon">
              <BookOpen size={22} aria-hidden="true" />
            </div>
            <div className="reader-heading-copy">
              <div className="reader-meta">
                {gradeLabel(book, t)} <span aria-hidden="true">·</span> {book.subject}
              </div>
              <h1>{book.title}</h1>
              <p>{book.chapter}</p>
            </div>
            <div className="reader-page-count">
              <strong>{book.pages}</strong>
              <span>{t.pages}</span>
            </div>
          </header>

          <section className="reader-document" aria-label={t.bookContent}>
            <div className="reader-document-bar">
              <span className="reader-document-label">
                <BookOpen size={18} aria-hidden="true" />
                {t.bookContent}
              </span>
              <span>
                {book.pages} {t.pages}
              </span>
            </div>
            {isTextFile ? (
              <article className="reader-document-frame reader-text">
                <pre>{text}</pre>
              </article>
            ) : (
              <div className="reader-document-frame">
                <iframe
                  title={`${t.bookContent}: ${book.title}`}
                  src={`/api/textbooks/${book.id}/file#toolbar=1&navpanes=0&view=FitH`}
                />
              </div>
            )}
          </section>
        </>
      )}
    </section>
  )
}
