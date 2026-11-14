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
  role,
  currentUserId,
}: {
  t: Copy
  role: 'admin' | 'teacher'
  currentUserId: string
}) {
  const requiresStaffListener = isStudentListener()
  const [data, setData] = useState<TeacherDashboardData | null>(null)
  const [accounts, setAccounts] = useState<AccountUser[]>([])
  const [selectedClass, setSelectedClass] = useState('')
  const [students, setStudents] = useState<Learner[]>([])
  const [sessions, setSessions] = useState<TutorSession[]>([])
  const [transcript, setTranscript] = useState<Transcript | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [accountFilter, setAccountFilter] = useState('')
  const [temporaryCredential, setTemporaryCredential] = useState<{
    userId: string
    password: string
  } | null>(null)

  const refreshDashboard = useCallback(async () => {
    const result = await api<TeacherDashboardData>('/teacher/dashboard')
    setData(result)
    setSelectedClass((current) => current || result.classes[0]?.id || '')
  }, [])
  const refreshAccounts = useCallback(async () => {
    if (role === 'admin') {
      setAccounts(await api<AccountUser[]>('/admin/users?include_disabled=true'))
    }
  }, [role])
  useEffect(() => {
    if (requiresStaffListener) {
      window.location.replace(staffPortalUrl('/teacher'))
      return
    }
    refreshDashboard().catch(setError)
    refreshAccounts().catch(setError)
  }, [refreshDashboard, refreshAccounts, requiresStaffListener])
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
          ...(role === 'admin' ? { teacher_id: form.get('teacher_id') } : {}),
        }),
      })
      await refreshDashboard()
      await refreshAccounts()
      setSelectedClass(created.id)
      setNotice(t.createClass)
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
    try {
      await api('/teacher/students', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.get('username'),
          display_name: form.get('display_name'),
          password: form.get('password'),
          grade: current?.grade,
          class_id: selectedClass,
        }),
      })
      await refreshDashboard()
      const nextStudents = await api<Learner[]>(`/teacher/classes/${selectedClass}/students`)
      setStudents(nextStudents)
      setNotice(t.addLearner)
      element.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function createTeacher(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const element = event.currentTarget
    const form = new FormData(element)
    try {
      await api('/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.get('username'),
          display_name: form.get('display_name'),
          password: form.get('password'),
          role: 'teacher',
        }),
      })
      await refreshAccounts()
      setNotice(t.createTeacher)
      element.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  function makeTemporaryPassword() {
    const bytes = window.crypto.getRandomValues(new Uint8Array(18))
    return `Temp-${Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')}`
  }

  async function resetPassword(user: AccountUser | Learner) {
    const password = makeTemporaryPassword()
    setBusy(true)
    setError(null)
    try {
      if (user.role === 'student' && role === 'teacher') {
        if (!selectedClass) return
        await api(`/teacher/classes/${selectedClass}/students/${user.id}/password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ temporary_password: password }),
        })
      } else {
        await api(`/admin/users/${user.id}/password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ temporary_password: password }),
        })
      }
      setTemporaryCredential({ userId: user.id, password })
      setNotice(t.passwordResetDone)
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function setAccountDisabled(user: AccountUser, disabled: boolean) {
    setBusy(true)
    setError(null)
    try {
      await api(`/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ disabled }),
      })
      await refreshAccounts()
      setNotice(t.accountUpdated)
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  const visibleAccounts = accounts.filter((item) =>
    `${item.display_name} ${item.username} ${item.role}`
      .toLocaleLowerCase()
      .includes(accountFilter.trim().toLocaleLowerCase()),
  )

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
      {role === 'admin' && (
        <form className="panel account-form" onSubmit={createTeacher}>
          <h2>{t.createTeacher}</h2>
          <Field label={t.displayName}>
            <input name="display_name" required maxLength={80} />
          </Field>
          <Field label={t.username}>
            <input name="username" required minLength={3} maxLength={48} />
          </Field>
          <Field label={t.password}>
            <input name="password" type="password" required minLength={12} maxLength={128} />
          </Field>
          <button className="primary" disabled={busy}>
            {t.createTeacher}
          </button>
        </form>
      )}
      {role === 'admin' && (
        <section className="panel account-section">
          <div className="section-heading-row account-management-heading">
            <h2>{t.accountManagement}</h2>
            <Field label={t.filterAccounts}>
              <input
                value={accountFilter}
                onChange={(event) => setAccountFilter(event.target.value)}
                type="search"
              />
            </Field>
          </div>
          {visibleAccounts.length ? (
            <ul className="learner-list">
              {visibleAccounts.map((item) => (
                <li key={item.id}>
                  <div className="account-details">
                    <strong>{item.display_name}</strong>
                    <span>
                      {item.username} · {item.role}
                    </span>
                    <small>
                      {item.disabled
                        ? t.disabledAccount
                        : item.must_change_password
                          ? t.passwordChangeRequired
                          : t.activeAccount}
                    </small>
                    {temporaryCredential?.userId === item.id && (
                      <code className="temporary-credential">{temporaryCredential.password}</code>
                    )}
                  </div>
                  <div className="account-row-actions">
                    <button
                      className="text-button"
                      disabled={busy || item.disabled || item.id === currentUserId}
                      onClick={() => void resetPassword(item)}
                    >
                      {t.resetPassword}
                    </button>
                    {item.id !== currentUserId && (
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() => void setAccountDisabled(item, !item.disabled)}
                      >
                        {item.disabled ? t.restoreAccount : t.deactivateAccount}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">{accountFilter ? t.noMatchingAccounts : t.noTeachers}</p>
          )}
        </section>
      )}
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
        {(role === 'teacher' || role === 'admin') && (
          <form className="inline-account-form" onSubmit={createClass}>
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
            {role === 'admin' && (
              <Field label={t.assignedTeacher}>
                <select name="teacher_id" required defaultValue="">
                  <option value="" disabled>
                    {t.chooseTeacher}
                  </option>
                  {accounts
                    .filter((item) => item.role === 'teacher')
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.display_name}
                      </option>
                    ))}
                </select>
              </Field>
            )}
            <button className="secondary" disabled={busy}>
              {t.createClass}
            </button>
          </form>
        )}
      </section>
      {selectedClass && (
        <>
          {(role === 'teacher' || role === 'admin') && (
            <form className="panel account-form" onSubmit={createLearner}>
              <h2>{t.addLearner}</h2>
              <Field label={t.displayName}>
                <input name="display_name" required maxLength={80} />
              </Field>
              <Field label={t.learnerUsername}>
                <input name="username" required minLength={3} maxLength={48} />
              </Field>
              <Field label={t.learnerPassword}>
                <input name="password" type="password" required minLength={12} maxLength={128} />
              </Field>
              <button className="primary" disabled={busy}>
                {t.addLearner}
              </button>
            </form>
          )}
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
                      {temporaryCredential?.userId === student.id && (
                        <code className="temporary-credential">{temporaryCredential.password}</code>
                      )}
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
