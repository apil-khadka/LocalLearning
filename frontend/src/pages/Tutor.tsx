import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { BookOpen, ChatCircleDots, PaperPlaneTilt, Sparkle } from '@phosphor-icons/react'
import ReactMarkdown from 'react-markdown'
import { Link, useSearchParams } from 'react-router-dom'
import {
  api,
  readerLink,
  type AccountUser,
  type Book,
  type Reply,
  type Services,
  type TutorMode,
  type TutorMessage,
} from '../lib/api'
import type { Copy, Language } from '../lib/i18n'
import { ErrorNotice, Field, Status } from '../components/ui'

type Message = { role: 'user' | 'assistant'; content: string; attempt?: string; reply?: Reply }

const modes: TutorMode[] = ['explain', 'hint', 'debug']
const commonSubjects = [
  'Science',
  'Mathematics',
  'English',
  'Nepali',
  'Social Studies',
  'Health and Physical Education',
  'Computer Science',
]

function starterPromptsFor(subject: string, language: Language): string[] {
  const lower = subject.toLowerCase()
  if (lower.includes('science')) {
    return language === 'ne'
      ? [
          'चाल र वेग भनेको के हो? यिनीहरूबीच के फरक छ?',
          'वनस्पतिमा प्रकाश संश्लेषण किन महत्त्वपूर्ण छ?',
        ]
      : [
          'What is speed and velocity? How are they different?',
          'Why is photosynthesis important for living things?',
        ]
  }
  if (lower.includes('math')) {
    return language === 'ne'
      ? [
          'उचित उपसमुच्च र अनुचित उपसमुच्चबीच के फरक छ?',
          'परिमेय र अपरिमेय संख्या कसरी चिन्ने?',
        ]
      : [
          'What is the difference between a proper and improper subset?',
          'How do rational and irrational numbers differ?',
        ]
  }
  return []
}

export default function Tutor({
  t,
  language,
  services,
  account,
  authReady,
  authRequired,
}: {
  t: Copy
  language: Language
  services: Services | null
  account: AccountUser | null
  authReady: boolean
  authRequired: boolean
}) {
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedSession = searchParams.get('session')
  const [grade, setGrade] = useState('8')
  const [subject, setSubject] = useState('Science')
  const [chapter, setChapter] = useState('')
  const [books, setBooks] = useState<Book[]>([])
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<TutorMode>('explain')
  const [attempt, setAttempt] = useState('')
  const [hintLevel, setHintLevel] = useState(0)
  const [messages, setMessages] = useState<Message[]>([])
  const [pendingTurn, setPendingTurn] = useState<{ question: string; attempt?: string } | null>(
    null,
  )
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const subjectTouchedRef = useRef(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    api<Book[]>(`/textbooks?grade=${grade}`, { signal: controller.signal })
      .then((loaded) => {
        setBooks(loaded)
        if (!subjectTouchedRef.current) {
          const hasScience = loaded.some((b) => b.subject.toLowerCase() === 'science')
          const sciTech = loaded.find(
            (b) => b.subject.toLowerCase() === 'science and technology',
          )?.subject
          if (!hasScience && sciTech) {
            setSubject((current) => (current === 'Science' ? sciTech : current))
          }
        }
      })
      .catch(() => setBooks([]))
    return () => controller.abort()
  }, [grade])
  useEffect(() => {
    if (account?.role === 'student' && account.grade) setGrade(String(account.grade))
  }, [account?.id, account?.grade, account?.role])
  useEffect(() => {
    if (!authReady || !account || !requestedSession) return
    api<{
      id: string
      grade: number
      subject: string
      chapter: string
      language: Language
      mode: TutorMode
      hint_level: number
      messages: TutorMessage[]
    }>(`/account/sessions/${requestedSession}`)
      .then((saved) => {
        subjectTouchedRef.current = true
        setSessionId(saved.id)
        setGrade(String(saved.grade))
        setSubject(saved.subject)
        setChapter(saved.chapter)
        setMode(saved.mode)
        setHintLevel(saved.hint_level)
        setMessages(
          saved.messages.map((message) => ({
            role: message.role,
            content: message.content,
            ...(message.attempt ? { attempt: message.attempt } : {}),
            ...(message.role === 'assistant'
              ? {
                  reply: {
                    answer: message.content,
                    grounding: message.grounding ?? 'general',
                    sources: message.sources,
                    model: 'saved-session',
                    mode: message.mode ?? saved.mode,
                    session_id: saved.id,
                  },
                }
              : {}),
          })),
        )
      })
      .catch(setError)
  }, [account, authReady, requestedSession])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, pendingTurn])

  const chapters = [
    ...new Set(
      books
        .filter((b) => b.subject.toLowerCase() === subject.trim().toLowerCase())
        .map((b) => b.chapter),
    ),
  ]
  const subjects = [
    ...new Map(
      [...books.map((book) => book.subject), ...commonSubjects, subject]
        .map((value) => value.trim())
        .filter(Boolean)
        .map((value) => [value.toLowerCase(), value] as const),
    ).values(),
  ]
  const starterPrompts = starterPromptsFor(subject, language)

  const reset = () => {
    setMessages([])
    setPendingTurn(null)
    setSessionId(null)
    setHintLevel(0)
    setError(null)
    if (requestedSession) setSearchParams({}, { replace: true })
  }
  async function send(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || busy || (mode === 'debug' && !attempt.trim())) return
    const content = question.trim()
    const trimmedAttempt = attempt.trim()
    setBusy(true)
    setError(null)
    setPendingTurn({
      question: content,
      ...(mode === 'debug' && trimmedAttempt ? { attempt: trimmedAttempt } : {}),
    })
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
          mode,
          hint_level: hintLevel,
          ...(sessionId ? { session_id: sessionId } : {}),
          ...(mode === 'debug' ? { attempt: trimmedAttempt } : {}),
          history: messages
            .slice(-8)
            .map(({ role, content }) => ({ role, content: content.slice(0, 3000) })),
        }),
      })
      setMessages((previous) => [
        ...previous,
        { role: 'user', content, ...(mode === 'debug' && trimmedAttempt ? { attempt: trimmedAttempt } : {}) },
        { role: 'assistant', content: reply.answer, reply },
      ])
      if (reply.session_id) {
        setSessionId(reply.session_id)
        setSearchParams({ session: reply.session_id }, { replace: true })
      }
      setQuestion('')
      setAttempt('')
      if (mode === 'hint') setHintLevel((level) => Math.min(4, level + 1))
    } catch (e) {
      setError(e)
    } finally {
      setPendingTurn(null)
      setBusy(false)
    }
  }
  function handleQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (!busy && question.trim() && subject.trim() && (mode !== 'debug' || attempt.trim())) {
        formRef.current?.requestSubmit()
      }
    }
  }
  if (!authReady) return <p role="status">{t.loading}</p>
  if (account?.must_change_password) {
    return (
      <section className="panel account-page">
        <h1>{t.changePassword}</h1>
        <p>{t.changePasswordIntro}</p>
        <Link className="primary" to="/change-password">
          {t.changePassword}
        </Link>
      </section>
    )
  }
  if (authRequired && !account) {
    return (
      <section className="panel account-page">
        <h1>{t.signIn}</h1>
        <p>{t.tutorSignInRequired}</p>
        <Link className="primary" to="/login">
          {t.signIn}
        </Link>
      </section>
    )
  }
  return (
    <>
      <header className="page-heading">
        <h1>{t.tutor}</h1>
        <p>{t.tutorIntro}</p>
      </header>
      <div className="tutor-layout">
        <aside className="tutor-context">
          <div className="tutor-context-header">
            <h2>{t.chapter}</h2>
            {services && <Status value={services.tutor.status} t={t} />}
          </div>
          <fieldset disabled={busy}>
            <div className="tutor-fields">
              <Field label={t.grade}>
                <select
                  value={grade}
                  disabled={busy || (account?.role === 'student' && account.grade !== null)}
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
                <select
                  value={subject}
                  required
                  onChange={(e) => {
                    subjectTouchedRef.current = true
                    setSubject(e.target.value)
                    setChapter('')
                    reset()
                  }}
                >
                  {subjects.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
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
            </div>
            <fieldset className="mode-picker" disabled={busy}>
              <legend>{t.learningMode}</legend>
              {modes.map((value) => (
                <label key={value}>
                  <input
                    type="radio"
                    name="mode"
                    value={value}
                    checked={mode === value}
                    onChange={() => {
                      setMode(value)
                      setHintLevel(0)
                    }}
                  />
                  <span>
                    <strong>{t[`mode_${value}`]}</strong>
                    <small>{t[`mode_${value}_note`]}</small>
                  </span>
                </label>
              ))}
            </fieldset>
          </fieldset>
          <p className="small-note">{t.teacherNote}</p>
          {account?.role === 'student' && <p className="small-note">{t.sessionPrivacyNotice}</p>}
        </aside>
        <div className="conversation">
          <div className="messages" role="log" aria-label={t.tutor} aria-live="polite">
            {!messages.length && !pendingTurn && (
              <div className="empty-chat">
                <span className="resource-icon blue">
                  <ChatCircleDots size={34} aria-hidden="true" />
                </span>
                <h2>{t.emptyChat}</h2>
                <p>{t.emptyChatNote}</p>
                <div className="starter-prompts" aria-label={t.starterPromptsLabel}>
                  <button
                    type="button"
                    className="practice"
                    onClick={() => setQuestion(t.sampleQuestion)}
                  >
                    <Sparkle size={18} aria-hidden="true" />
                    {t.practice}
                  </button>
                  {starterPrompts.map((prompt) => (
                    <button
                      type="button"
                      key={prompt}
                      className="starter-chip"
                      onClick={() => setQuestion(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, i) => (
              <article key={i} className={`message ${message.role}`}>
                <strong>{message.role === 'user' ? t.question : t.tutor}</strong>
                {message.role === 'assistant' ? (
                  <div className="message-content">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="message-content">{message.content}</p>
                )}
                {message.attempt && (
                  <p className="message-attempt">
                    <strong>{t.yourAttempt}:</strong> {message.attempt}
                  </p>
                )}
                {message.reply && (
                  <div className="message-meta">
                    <span className={`grounding-badge grounding-${message.reply.grounding}`}>
                      {message.reply.grounding === 'textbook'
                        ? t.grounded
                        : message.reply.grounding === 'note'
                          ? t.groundedNote
                          : t.general}
                    </span>
                    {message.reply.sources.length > 0 && (
                      <div className="sources">
                        <span className="sources-label">{t.sources}</span>
                        <div className="source-list">
                          {message.reply.sources.map((source) => (
                            <Link
                              key={source.chunk_id}
                              className="source-chip"
                              to={readerLink(source.document_id, source.page_start)}
                            >
                              <BookOpen size={15} aria-hidden="true" />
                              <span>
                                {source.kind === 'note' ? `${t.teacherNoteLabel}: ` : ''}
                                {source.title}, {t.pages} {source.page_start}
                              </span>
                            </Link>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </article>
            ))}
            {pendingTurn && (
              <>
                <article className="message pending-user">
                  <strong>{t.question}</strong>
                  <p className="message-content">{pendingTurn.question}</p>
                  {pendingTurn.attempt && (
                    <p className="message-attempt">
                      <strong>{t.yourAttempt}:</strong> {pendingTurn.attempt}
                    </p>
                  )}
                </article>
                <div className="thinking-bubble" role="status">
                  <span className="thinking-dots" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </span>
                  <span>{t.thinking}</span>
                </div>
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
          <ErrorNotice error={error} t={t} />
          <form ref={formRef} className="composer" onSubmit={send}>
            <Field label={t.question}>
              <textarea
                value={question}
                maxLength={2000}
                required
                rows={3}
                placeholder={t.questionHint}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleQuestionKeyDown}
              />
            </Field>
            {mode === 'debug' && (
              <Field label={t.yourAttempt}>
                <textarea
                  value={attempt}
                  maxLength={2000}
                  required
                  rows={3}
                  placeholder={t.yourAttemptHint}
                  onChange={(e) => setAttempt(e.target.value)}
                />
              </Field>
            )}
            {mode === 'hint' && (
              <p className="small-note" role="status">
                {t.hintStep} {hintLevel + 1} / 5
              </p>
            )}
            <p className="small-note composer-hint">{t.enterToSendHint}</p>
            <div className="composer-actions">
              <button
                type="button"
                className="text-button"
                disabled={busy || !messages.length}
                onClick={reset}
              >
                {t.clear}
              </button>
              <button
                className="primary"
                disabled={
                  busy ||
                  !question.trim() ||
                  !subject.trim() ||
                  (mode === 'debug' && !attempt.trim())
                }
              >
                <PaperPlaneTilt size={19} aria-hidden="true" />
                {busy
                  ? t.thinking
                  : mode === 'hint'
                    ? t.getHint
                    : mode === 'debug'
                      ? t.checkWork
                      : t.send}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
