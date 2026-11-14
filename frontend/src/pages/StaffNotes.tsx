import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  api,
  ApiError,
  type AccountUser,
  type Book,
  type NoteFields,
  type PageRange,
  type StaffNote,
} from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

type Draft = {
  title: string
  grade: string
  subject: string
  chapter: string
  language: 'en' | 'ne'
  document_id: string
  pages: string
  key_ideas: string
  worked_example: string
  misconceptions: string
  hints: string
  check_question: string
  kolibri_channel_id: string
}

const blank: Draft = {
  title: '',
  grade: '8',
  subject: '',
  chapter: '',
  language: 'en',
  document_id: '',
  pages: '',
  key_ideas: '',
  worked_example: '',
  misconceptions: '',
  hints: '',
  check_question: '',
  kolibri_channel_id: '',
}

const lines = (text: string) =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)

/** Parse "3, 5-7" into page ranges; returns null when any part is malformed. */
function parsePages(text: string): PageRange[] | null {
  const ranges: PageRange[] = []
  for (const part of text.split(',').map((p) => p.trim())) {
    const match = /^(\d{1,4})(?:\s*[-–]\s*(\d{1,4}))?$/.exec(part)
    if (!match) return null
    const start = Number(match[1])
    const end = match[2] ? Number(match[2]) : start
    if (start < 1 || end < start) return null
    ranges.push({ start, end })
  }
  return ranges.length ? ranges : null
}

function toFields(draft: Draft): NoteFields | null {
  const pages = parsePages(draft.pages)
  if (!pages) return null
  return {
    title: draft.title,
    grade: Number(draft.grade),
    subject: draft.subject,
    chapter: draft.chapter,
    language: draft.language,
    document_id: draft.document_id,
    pages,
    key_ideas: lines(draft.key_ideas),
    worked_example: draft.worked_example,
    misconceptions: lines(draft.misconceptions).map((line) => {
      const [wrong, ...rest] = line.split('|')
      return { wrong: wrong.trim(), correction: rest.join('|').trim() }
    }),
    hints: lines(draft.hints),
    check_question: draft.check_question,
    kolibri_channel_id: draft.kolibri_channel_id.trim() || null,
  }
}

function toDraft(note: StaffNote): Draft {
  return {
    ...note,
    grade: String(note.grade),
    pages: note.pages
      .map((p) => (p.start === p.end ? `${p.start}` : `${p.start}-${p.end}`))
      .join(', '),
    key_ideas: note.key_ideas.join('\n'),
    misconceptions: note.misconceptions.map((m) => `${m.wrong} | ${m.correction}`).join('\n'),
    hints: note.hints.join('\n'),
    kolibri_channel_id: note.kolibri_channel_id ?? '',
  }
}

export default function StaffNotes({
  t,
  documents,
  account,
}: {
  t: Copy
  documents: Book[]
  account: Pick<AccountUser, 'id' | 'role'>
}) {
  const [notes, setNotes] = useState<StaffNote[]>([])
  const [draft, setDraft] = useState<Draft>(blank)
  const [editing, setEditing] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const headers = { 'Content-Type': 'application/json' }
  const books = documents.filter((d) => d.status === 'ready')
  const set = (key: keyof Draft, value: string) => setDraft((d) => ({ ...d, [key]: value }))

  const load = useCallback(async () => {
    setNotes(await api<StaffNote[]>('/admin/notes'))
  }, [])
  useEffect(() => {
    load().catch(setError)
  }, [load])

  async function run(action: () => Promise<unknown>) {
    setBusy(true)
    setError(null)
    try {
      await action()
      await load()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  function save(event: FormEvent) {
    event.preventDefault()
    const fields = toFields(draft)
    if (!fields) {
      setError(new ApiError(t.pagesInvalid, null))
      return
    }
    void run(async () => {
      await api(editing ? `/admin/notes/${editing}` : '/admin/notes', {
        method: editing ? 'PUT' : 'POST',
        headers,
        body: JSON.stringify(fields),
      })
      setDraft(blank)
      setEditing('')
    })
  }
  const review = (note: StaffNote, status: StaffNote['status']) =>
    run(() =>
      api(`/admin/notes/${note.id}/review`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ status }),
      }),
    )

  return (
    <section className="panel staff-notes" aria-labelledby="notes-heading">
      <h2 id="notes-heading">{t.teachingNotes}</h2>
      <p className="small-note">{t.teachingNotesIntro}</p>
      <ErrorNotice error={error} t={t} />
      <form onSubmit={save} className="staff-note-form">
        <Field label={t.noteTitle}>
          <input
            required
            maxLength={120}
            value={draft.title}
            onChange={(e) => set('title', e.target.value)}
          />
        </Field>
        <Field label={t.linkedBook}>
          <select
            required
            value={draft.document_id}
            onChange={(e) => {
              const book = books.find((b) => b.id === e.target.value)
              setDraft((d) => ({
                ...d,
                document_id: e.target.value,
                ...(book
                  ? {
                      grade: book.grade ? String(book.grade) : d.grade,
                      subject: d.subject || book.subject,
                      chapter: d.chapter || book.chapter,
                    }
                  : {}),
              }))
            }}
          >
            <option value="">{t.chooseBook}</option>
            {books.map((b) => (
              <option key={b.id} value={b.id}>
                {b.title} ({b.pages} {t.pages})
              </option>
            ))}
          </select>
        </Field>
        <Field label={t.sourcePagesField}>
          <input
            required
            placeholder="12, 14-15"
            value={draft.pages}
            onChange={(e) => set('pages', e.target.value)}
          />
        </Field>
        <Field label={t.noteGrade}>
          <select value={draft.grade} onChange={(e) => set('grade', e.target.value)}>
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i}>{i + 1}</option>
            ))}
          </select>
        </Field>
        <Field label={t.noteSubject}>
          <input
            required
            maxLength={120}
            value={draft.subject}
            onChange={(e) => set('subject', e.target.value)}
          />
        </Field>
        <Field label={t.noteChapter}>
          <input
            maxLength={120}
            value={draft.chapter}
            onChange={(e) => set('chapter', e.target.value)}
          />
        </Field>
        <Field label={t.noteLanguage}>
          <select value={draft.language} onChange={(e) => set('language', e.target.value)}>
            <option value="en">English</option>
            <option value="ne">नेपाली</option>
          </select>
        </Field>
        <Field label={t.keyIdeasField}>
          <textarea
            required
            rows={4}
            value={draft.key_ideas}
            onChange={(e) => set('key_ideas', e.target.value)}
          />
        </Field>
        <Field label={t.workedExample}>
          <textarea
            rows={3}
            maxLength={1500}
            value={draft.worked_example}
            onChange={(e) => set('worked_example', e.target.value)}
          />
        </Field>
        <Field label={t.misconceptionsField}>
          <textarea
            rows={3}
            value={draft.misconceptions}
            onChange={(e) => set('misconceptions', e.target.value)}
          />
        </Field>
        <Field label={t.hintsField}>
          <textarea rows={3} value={draft.hints} onChange={(e) => set('hints', e.target.value)} />
        </Field>
        <Field label={t.checkQuestionField}>
          <input
            maxLength={500}
            value={draft.check_question}
            onChange={(e) => set('check_question', e.target.value)}
          />
        </Field>
        <Field label={t.kolibriChannelField}>
          <input
            pattern="[a-f0-9]{32}"
            title="32 lowercase hexadecimal characters"
            value={draft.kolibri_channel_id}
            onChange={(e) => set('kolibri_channel_id', e.target.value)}
          />
        </Field>
        <div className="composer-actions">
          {editing && (
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setDraft(blank)
                setEditing('')
              }}
            >
              {t.cancelEdit}
            </button>
          )}
          <button className="primary" disabled={busy}>
            {editing ? t.saveNote : t.createNote}
          </button>
        </div>
        {editing && <p className="small-note">{t.editResetsReview}</p>}
      </form>

      <h3>{t.noteList}</h3>
      {notes.length === 0 ? (
        <p className="small-note">{t.noNotesStaff}</p>
      ) : (
        <ul className="staff-note-list">
          {notes.map((note) => (
            <li key={note.id}>
              <strong>{note.title}</strong>
              <span className={`note-status note-${note.status}`}>{t[`note_${note.status}`]}</span>
              <small>
                {t.grade} {note.grade} · {note.subject} · v{note.revision}
                {note.reviewer ? ` · ${t.reviewedBy} ${note.reviewer}` : ''}
              </small>
              <div className="note-actions">
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => {
                    setDraft(toDraft(note))
                    setEditing(note.id)
                  }}
                >
                  {t.editNote}
                </button>
                {note.status === 'draft' && (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => review(note, 'in_review')}
                  >
                    {t.submitForReview}
                  </button>
                )}
                {note.status === 'in_review' &&
                  (account.role === 'admin' || note.author_id !== account.id ? (
                    <button
                      className="primary"
                      disabled={busy}
                      onClick={() => review(note, 'approved')}
                    >
                      {t.approveNote}
                    </button>
                  ) : (
                    <small>{t.otherReviewerRequired}</small>
                  ))}
                {note.status !== 'draft' && (
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => review(note, 'draft')}
                  >
                    {t.returnToDraft}
                  </button>
                )}
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(t.confirmDeleteNote))
                      void run(() => api(`/admin/notes/${note.id}`, { method: 'DELETE', headers }))
                  }}
                >
                  {t.deleteNote}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
