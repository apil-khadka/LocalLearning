import { useEffect, useState, type FormEvent } from 'react'
import { ChatCircleDots, PaperPlaneTilt, Sparkle } from '@phosphor-icons/react'
import { api, type Book, type Reply, type Services } from '../lib/api'
import type { Copy, Language } from '../lib/i18n'
import { ErrorNotice, Field, Status } from '../components/ui'

type Message = { role: 'user' | 'assistant'; content: string; reply?: Reply }

export default function Tutor({
  t,
  language,
  services,
}: {
  t: Copy
  language: Language
  services: Services | null
}) {
  const [grade, setGrade] = useState('8')
  const [subject, setSubject] = useState('Science')
  const [chapter, setChapter] = useState('')
  const [books, setBooks] = useState<Book[]>([])
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    api<Book[]>(`/textbooks?grade=${grade}`, { signal: controller.signal })
      .then(setBooks)
      .catch(() => setBooks([]))
    return () => controller.abort()
  }, [grade])
  const chapters = [
    ...new Set(
      books
        .filter((b) => b.subject.toLowerCase() === subject.trim().toLowerCase())
        .map((b) => b.chapter),
    ),
  ]
  const reset = () => {
    setMessages([])
    setError(null)
  }
  async function send(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || busy) return
    setBusy(true)
    setError(null)
    const content = question.trim()
    try {
      const reply = await api<Reply>('/tutor/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          grade: Number(grade),
          subject,
          chapter,
          language,
          history: messages
            .slice(-8)
            .map(({ role, content }) => ({ role, content: content.slice(0, 3000) })),
        }),
      })
      setMessages((previous) => [
        ...previous,
        { role: 'user', content },
        { role: 'assistant', content: reply.answer, reply },
      ])
      setQuestion('')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <header className="page-heading">
        <h1>{t.tutor}</h1>
        <p>{t.tutorIntro}</p>
      </header>
      <div className="tutor-layout">
        <aside className="tutor-context">
          <h2>{t.chapter}</h2>
          <fieldset disabled={busy}>
            <Field label={t.grade}>
              <select
                value={grade}
                onChange={(e) => {
                  setGrade(e.target.value)
                  setChapter('')
                  reset()
                }}
              >
                {Array.from({ length: 12 }, (_, i) => (
                  <option key={i} value={i + 1}>
                    {i + 1}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t.subject}>
              <input
                value={subject}
                maxLength={120}
                required
                onChange={(e) => {
                  setSubject(e.target.value)
                  setChapter('')
                  reset()
                }}
              />
            </Field>
            <Field label={t.chapter}>
              <select
                value={chapter}
                onChange={(e) => {
                  setChapter(e.target.value)
                  reset()
                }}
              >
                <option value="">{t.allChapters}</option>
                {chapters.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </Field>
          </fieldset>
          {services && <Status value={services.tutor.status} t={t} />}
          <p className="small-note">{t.teacherNote}</p>
        </aside>
        <div className="conversation">
          <div className="messages" role="log" aria-label={t.tutor} aria-live="polite">
            {!messages.length && (
              <div className="empty-chat">
                <span className="resource-icon blue">
                  <ChatCircleDots size={34} aria-hidden="true" />
                </span>
                <h2>{t.emptyChat}</h2>
                <p>{t.emptyChatNote}</p>
                <button className="practice" onClick={() => setQuestion(t.sampleQuestion)}>
                  <Sparkle size={18} aria-hidden="true" />
                  {t.practice}
                </button>
              </div>
            )}
            {messages.map((message, i) => (
              <article key={i} className={`message ${message.role}`}>
                <strong>{message.role === 'user' ? t.question : t.tutor}</strong>
                <p>{message.content}</p>
                {message.reply && (
                  <>
                    <small>{message.reply.grounding === 'textbook' ? t.grounded : t.general}</small>
                    {message.reply.sources.length > 0 && (
                      <div className="sources">
                        <span>{t.sources}</span>
                        {message.reply.sources.map((source) => (
                          <a
                            key={source.chunk_id}
                            href={`/api/textbooks/${source.document_id}/file#page=${source.page_start}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {source.title}, {t.pages} {source.page_start}
                          </a>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </article>
            ))}
            {busy && <p role="status">{t.thinking}</p>}
          </div>
          <ErrorNotice error={error} t={t} />
          <form className="composer" onSubmit={send}>
            <Field label={t.question}>
              <textarea
                value={question}
                maxLength={2000}
                required
                rows={3}
                placeholder={t.questionHint}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </Field>
            <div className="composer-actions">
              <button
                type="button"
                className="text-button"
                disabled={busy || !messages.length}
                onClick={reset}
              >
                {t.clear}
              </button>
              <button className="primary" disabled={busy || !question.trim() || !subject.trim()}>
                <PaperPlaneTilt size={19} aria-hidden="true" />
                {busy ? t.thinking : t.send}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
