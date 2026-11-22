import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  api,
  isStudentListener,
  staffPortalUrl,
  type AccountUser,
  type TeacherDashboardData,
  type TutorMessage,
  type TutorSession,
} from '../lib/api'
import { Link } from 'react-router-dom'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'
import TemporaryCredentials, {
  type TemporaryCredentialsData,
} from '../components/TemporaryCredentials'
import { generateTemporaryPassword } from '../lib/accounts'

type Learner = {
  id: string
  username: string
  display_name: string
  role: 'student'
  grade: number | null
  session_count: number
}
type Transcript = TutorSession & {
  messages: TutorMessage[]
}

export default function TeacherDashboard({
  t,
}: {
  t: Copy
}) {
  const requiresStaffListener = isStudentListener()
  const [data, setData] = useState<TeacherDashboardData | null>(null)
  const [selectedClass, setSelectedClass] = useState('')
  const [students, setStudents] = useState<Learner[]>([])
  const [sessions, setSessions] = useState<TutorSession[]>([])
  const [transcript, setTranscript] = useState<Transcript | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [credentials, setCredentials] = useState<TemporaryCredentialsData | null>(null)

  const refreshDashboard = useCallback(async () => {
    const result = await api<TeacherDashboardData>('/teacher/dashboard')
    setData(result)
    setSelectedClass((current) => current || result.classes[0]?.id || '')
  }, [])
  useEffect(() => {
    if (requiresStaffListener) {
      window.location.replace(staffPortalUrl('/teacher'))
      return
    }
    refreshDashboard().catch(setError)
  }, [refreshDashboard, requiresStaffListener])
  useEffect(() => {
    if (!selectedClass) {
      setStudents([])
      setSessions([])
      setTranscript(null)
      return
    }
    Promise.all([
      api<Learner[]>(`/teacher/classes/${selectedClass}/students`),
      api<TutorSession[]>(`/teacher/classes/${selectedClass}/sessions`),
    ])
      .then(([nextStudents, nextSessions]) => {
        setStudents(nextStudents)
        setSessions(nextSessions)
        setTranscript(null)
      })
      .catch(setError)
  }, [selectedClass])

  async function createClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const element = event.currentTarget
    const form = new FormData(element)
    try {
      const created = await api<{ id: string }>('/teacher/classes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.get('class_name'),
          grade: Number(form.get('grade')),
        }),
      })
      await refreshDashboard()
      setSelectedClass(created.id)
      setNotice(t.classCreated)
      element.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function createLearner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClass) return
    setBusy(true)
    setError(null)
    const element = event.currentTarget
    const form = new FormData(element)
    const current = data?.classes.find((item) => item.id === selectedClass)
    const password = generateTemporaryPassword()
    try {
      const created = await api<AccountUser>('/teacher/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.get('username'),
          display_name: form.get('display_name'),
          password,
          grade: current?.grade,
          class_id: selectedClass,
        }),
      })
      await refreshDashboard()
      const nextStudents = await api<Learner[]>(`/teacher/classes/${selectedClass}/students`)
      setStudents(nextStudents)
      setCredentials({
        displayName: created.display_name,
        username: created.username,
        password,
      })
      setNotice(t.learnerCreated)
      element.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword(user: Learner) {
    const password = generateTemporaryPassword()
    setBusy(true)
    setError(null)
    try {
      if (!selectedClass) return
      await api(`/teacher/classes/${selectedClass}/students/${user.id}/password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temporary_password: password }),
      })
      setCredentials({ displayName: user.display_name, username: user.username, password })
      setNotice(t.passwordResetDone)
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function openTranscript(session: TutorSession) {
    setError(null)
    try {
      const result = await api<Transcript>(
        `/teacher/sessions/${session.id}?class_id=${selectedClass}`,
      )
      setTranscript(result)
    } catch (cause) {
      setError(cause)
    }
  }

  if (requiresStaffListener) return <p role="status">{t.loading}</p>

  return (
    <section className="account-page">
      <header className="page-heading">
        <h1>{t.teacherDashboard}</h1>
        <p>{data?.user.display_name}</p>
        <Link className="button secondary button-link" to="/history">
          {t.myTutorHistory}
        </Link>
        <a className="button secondary button-link" href={staffPortalUrl('/staff')}>
          {t.staff}
        </a>
      </header>
      <ErrorNotice error={error} t={t} />
      {notice && (
        <p className="success-note" role="status">
          {notice}
        </p>
      )}
      {credentials && (
        <TemporaryCredentials
          t={t}
          credentials={credentials}
          onDismiss={() => setCredentials(null)}
          onCopyError={setError}
        />
      )}
      <div className="teacher-summary-row" aria-label={t.teacherDashboard}>
        <span>
          <strong>{data?.classes.length ?? 0}</strong> {t.assignedClasses.toLowerCase()}
        </span>
        <span>
          <strong>{data?.student_count ?? 0}</strong> {t.learners.toLowerCase()}
        </span>
        <span>
          <strong>{data?.session_count ?? 0}</strong> {t.tutorSessions.toLowerCase()}
        </span>
      </div>
      <section className="panel account-section">
        <div className="section-heading-row">
          <h2>{t.assignedClasses}</h2>
          {data?.classes.length ? (
            <select
              aria-label={t.assignedClasses}
              value={selectedClass}
              onChange={(event) => setSelectedClass(event.target.value)}
            >
              {data.classes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {t.grade} {item.grade}
                </option>
              ))}
            </select>
          ) : null}
        </div>
        {!data?.classes.length && <p className="empty-state">{t.noClasses}</p>}
        <form className="inline-account-form" aria-label={t.createClass} onSubmit={createClass}>
          <Field label={t.className}>
            <input name="class_name" required maxLength={80} />
          </Field>
          <Field label={t.grade}>
            <select name="grade" defaultValue="8">
              {Array.from({ length: 12 }, (_, i) => i + 1).map((grade) => (
                <option key={grade} value={grade}>
                  {grade}
                </option>
              ))}
            </select>
          </Field>
          <button className="secondary" disabled={busy}>
            {busy ? t.loading : t.createClass}
          </button>
        </form>
      </section>
      {selectedClass && (
        <>
          <form className="panel account-form" aria-labelledby="new-learner-title" onSubmit={createLearner}>
            <h2 id="new-learner-title">{t.addLearner}</h2>
            <p>{t.createLearnerHelp}</p>
            <Field label={t.displayName}>
              <input name="display_name" required maxLength={80} autoComplete="name" />
            </Field>
            <Field label={t.learnerUsername}>
              <input
                name="username"
                required
                minLength={3}
                maxLength={48}
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
              />
            </Field>
            <button className="primary" disabled={busy}>
              {busy ? t.loading : t.addLearner}
            </button>
          </form>
          <section className="panel account-section">
            <h2>{t.learners}</h2>
            {students.length ? (
              <ul className="learner-list">
                {students.map((student) => (
                  <li key={student.id}>
                    <div className="account-details">
                      <strong>{student.display_name}</strong>
                      <span>
                        {student.username} · {student.session_count} {t.tutorSessions.toLowerCase()}
                      </span>
                    </div>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => void resetPassword(student)}
                    >
                      {t.resetPassword}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">{t.noLearners}</p>
            )}
          </section>
          <section className="panel account-section">
            <h2>{t.tutorSessions}</h2>
            <p className="small-note">{t.transcriptAccessLogged}</p>
            {sessions.length ? (
              <div className="teacher-session-layout">
                <div className="teacher-session-list">
                  {sessions.map((session) => (
                    <button
                      key={session.id}
                      className="teacher-session-item"
                      onClick={() => openTranscript(session)}
                    >
                      <strong>{session.student_name}</strong>
                      <span>{session.title}</span>
                      <small>{new Date(session.updated_at).toLocaleString()}</small>
                    </button>
                  ))}
                </div>
                {transcript && (
                  <article className="teacher-transcript">
                    <h3>
                      {t.transcript}: {transcript.student_name}
                    </h3>
                    {transcript.messages.map((message, index) => (
                      <div
                        className={`message ${message.role}`}
                        key={`${message.created_at}-${index}`}
                      >
                        <strong>
                          {message.role === 'user' ? transcript.student_name : t.tutor}
                        </strong>
                        <p className="message-content">{message.content}</p>
                        {message.attempt && (
                          <p className="message-attempt">
                            <strong>{t.yourAttempt}:</strong> {message.attempt}
                          </p>
                        )}
                      </div>
                    ))}
                  </article>
                )}
              </div>
            ) : (
              <p className="empty-state">{t.noClassSessions}</p>
            )}
          </section>
        </>
      )}
    </section>
  )
}
