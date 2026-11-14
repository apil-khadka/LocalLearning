import { useEffect, useState } from 'react'
import { ArrowSquareOut, BookBookmark } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { api, readerLink, type StudyNote } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

function pageLabel(pages: StudyNote['pages']) {
  return pages.map((p) => (p.start === p.end ? `${p.start}` : `${p.start}–${p.end}`)).join(', ')
}

function NoteCard({ note, t }: { note: StudyNote; t: Copy }) {
  const [shownHints, setShownHints] = useState(0)
  return (
    <article className="study-note">
      <header>
        <span className="catalog-book-meta">
          {t.grade} {note.grade} <span aria-hidden="true">·</span> {note.subject}
          {note.chapter ? ` · ${note.chapter}` : ''}
        </span>
        <h2>{note.title}</h2>
        <p className="small-note">{t.reviewedNote}</p>
      </header>
      <section aria-label={t.keyIdeas}>
        <h3>{t.keyIdeas}</h3>
        <ul>
          {note.key_ideas.map((idea) => (
            <li key={idea}>{idea}</li>
          ))}
        </ul>
      </section>
      {note.worked_example && (
        <section aria-label={t.workedExample}>
          <h3>{t.workedExample}</h3>
          <p>{note.worked_example}</p>
        </section>
      )}
      {note.misconceptions.length > 0 && (
        <section aria-label={t.commonMistakes}>
          <h3>{t.commonMistakes}</h3>
          <ul>
            {note.misconceptions.map((m) => (
              <li key={m.wrong}>
                <strong>{m.wrong}</strong> {m.correction}
              </li>
            ))}
          </ul>
        </section>
      )}
      {(note.check_question || note.hints.length > 0) && (
        <section aria-label={t.tryIt} className="study-practice">
          <h3>{t.tryIt}</h3>
          {note.check_question && <p>{note.check_question}</p>}
          {note.hints.slice(0, shownHints).map((hint, index) => (
            <p key={hint} className="study-hint">
              <strong>
                {t.hintStep} {index + 1}:
              </strong>{' '}
              {hint}
            </p>
          ))}
          {shownHints < note.hints.length && (
            <button className="secondary" onClick={() => setShownHints((n) => n + 1)}>
              {t.showNextHint}
            </button>
          )}
          {note.check_question && (
            <p className="small-note">
              <Link to="/tutor">{t.needMoreHelp}</Link>
            </p>
          )}
        </section>
      )}
      <footer className="study-links">
        <span>
          {t.sourcePages}: {note.book_title}, {t.pages} {pageLabel(note.pages)}
        </span>
        {note.pages.map((p) => (
          <Link key={p.start} to={readerLink(note.document_id, p.start)}>
            {t.openBookAtPage} {p.start}
          </Link>
        ))}
        {note.kolibri_url && (
          <a href={note.kolibri_url} target="_blank" rel="noreferrer">
            {t.relatedKolibri} <ArrowSquareOut size={15} aria-hidden="true" />
          </a>
        )}
      </footer>
    </article>
  )
}

export default function Study({ t }: { t: Copy }) {
  const [notes, setNotes] = useState<StudyNote[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [grade, setGrade] = useState('')
  const [subject, setSubject] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setError(null)
    api<StudyNote[]>('/notes', { signal: controller.signal })
      .then(setNotes)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e)
      })
    return () => controller.abort()
  }, [attempt])
  const subjects = [...new Set((notes ?? []).map((n) => n.subject))].sort()
  const shown = (notes ?? []).filter(
    (n) => (!grade || n.grade === Number(grade)) && (!subject || n.subject === subject),
  )
  return (
    <>
      <header className="page-heading">
        <h1>{t.study}</h1>
        <p>{t.studyIntro}</p>
      </header>
      <ErrorNotice error={error} t={t} />
      {notes && notes.length > 0 && (
        <div className="catalog-toolbar study-filters">
          <Field label={t.grade}>
            <select value={grade} onChange={(e) => setGrade(e.target.value)}>
              <option value="">{t.allGrades}</option>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t.subject}>
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              <option value="">{t.allSubjects}</option>
              {subjects.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </Field>
        </div>
      )}
      {!notes && !error ? (
        <div className="catalog-loading" role="status">
          <span />
          <span />
        </div>
      ) : notes && shown.length === 0 ? (
        <div className="empty-state">
          <BookBookmark size={45} aria-hidden="true" />
          <h2>{t.noNotes}</h2>
          <p>{t.noNotesNote}</p>
        </div>
      ) : error ? (
        <button className="secondary" onClick={() => setAttempt((v) => v + 1)}>
          {t.retry}
        </button>
      ) : (
        <div className="study-list">
          {shown.map((note) => (
            <NoteCard key={note.id + note.revision} note={note} t={t} />
          ))}
        </div>
      )}
    </>
  )
}
