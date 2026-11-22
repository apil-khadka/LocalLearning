import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ErrorNotice, Field } from '../components/ui'
import TemporaryCredentials, {
  type TemporaryCredentialsData,
} from '../components/TemporaryCredentials'
import {
  api,
  isStudentListener,
  staffPortalUrl,
  type AccountUser,
  type TeacherDashboardData,
} from '../lib/api'
import { generateTemporaryPassword } from '../lib/accounts'
import type { Copy } from '../lib/i18n'

export default function AdminDashboard({ t }: { t: Copy }) {
  const requiresStaffListener = isStudentListener()
  const [dashboard, setDashboard] = useState<TeacherDashboardData | null>(null)
  const [accounts, setAccounts] = useState<AccountUser[]>([])
  const [credentials, setCredentials] = useState<TemporaryCredentialsData | null>(null)
  const [filter, setFilter] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const refreshDashboard = useCallback(async () => {
    setDashboard(await api<TeacherDashboardData>('/teacher/dashboard'))
  }, [])
  const refreshAccounts = useCallback(async () => {
    setAccounts(await api<AccountUser[]>('/admin/users?include_disabled=true'))
  }, [])

  useEffect(() => {
    if (requiresStaffListener) {
      window.location.replace(staffPortalUrl('/admin'))
      return
    }
    Promise.all([refreshDashboard(), refreshAccounts()])
      .catch(setError)
      .finally(() => setLoading(false))
  }, [refreshAccounts, refreshDashboard, requiresStaffListener])

  const teachers = accounts.filter((account) => account.role === 'teacher')
  const activeTeachers = teachers.filter((teacher) => !teacher.disabled)
  const visibleTeachers = teachers.filter((teacher) =>
    `${teacher.display_name} ${teacher.username}`
      .toLocaleLowerCase()
      .includes(filter.trim().toLocaleLowerCase()),
  )

  async function createTeacher(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setNotice('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const password = generateTemporaryPassword()
    try {
      const created = await api<AccountUser>('/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.get('username'),
          display_name: form.get('display_name'),
          password,
          role: 'teacher',
        }),
      })
      await refreshAccounts()
      setCredentials({
        displayName: created.display_name,
        username: created.username,
        password,
      })
      setNotice(t.teacherCreated)
      formElement.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function createClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setNotice('')
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    try {
      await api('/teacher/classes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.get('class_name'),
          grade: Number(form.get('grade')),
          teacher_id: form.get('teacher_id'),
        }),
      })
      await refreshDashboard()
      setNotice(t.classCreated)
      formElement.reset()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function resetPassword(teacher: AccountUser) {
    const password = generateTemporaryPassword()
    setBusy(true)
    setError(null)
    setNotice('')
    try {
      await api(`/admin/users/${teacher.id}/password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temporary_password: password }),
      })
      setCredentials({
        displayName: teacher.display_name,
        username: teacher.username,
        password,
      })
      setNotice(t.passwordResetDone)
      await refreshAccounts()
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  async function setTeacherDisabled(teacher: AccountUser, disabled: boolean) {
    setBusy(true)
    setError(null)
    setNotice('')
    try {
      await api(`/admin/users/${teacher.id}`, {
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

  if (requiresStaffListener) return <p role="status">{t.loading}</p>

  return (
    <section className="account-page admin-dashboard">
      <header className="page-heading">
        <div>
          <h1>{t.adminDashboard}</h1>
          <p>{t.adminDashboardIntro}</p>
        </div>
        <Link className="button secondary button-link" to="/staff">
          {t.staff}
        </Link>
      </header>
      <ErrorNotice error={error} t={t} />
      {notice && (
        <p className="success-note" role="status">
          {notice}
        </p>
      )}
      {!loading && dashboard && (
        <div className="teacher-summary-row admin-summary" aria-label={t.adminDashboard}>
          <span>
            <strong>{activeTeachers.length}</strong> {t.activeTeachers.toLowerCase()}
          </span>
          <span>
            <strong>{dashboard.classes.length}</strong> {t.schoolClasses.toLowerCase()}
          </span>
          <span>
            <strong>{dashboard.student_count}</strong> {t.learners.toLowerCase()}
          </span>
        </div>
      )}
      {credentials && (
        <TemporaryCredentials
          t={t}
          credentials={credentials}
          onDismiss={() => setCredentials(null)}
          onCopyError={setError}
        />
      )}
      <section className="panel account-section" aria-labelledby="new-teacher-title">
        <div className="section-heading-row admin-section-heading">
          <div>
            <h2 id="new-teacher-title">{t.createTeacher}</h2>
            <p>{t.createTeacherHelp}</p>
          </div>
        </div>
        <form className="admin-teacher-form" aria-labelledby="new-teacher-title" onSubmit={createTeacher}>
          <Field label={t.displayName}>
            <input name="display_name" required maxLength={80} autoComplete="name" />
          </Field>
          <Field label={t.username}>
            <input
              name="username"
              required
              minLength={3}
              maxLength={48}
              autoComplete="username"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="done"
            />
          </Field>
          <button className="primary" disabled={busy}>
            {busy ? t.loading : t.createTeacher}
          </button>
        </form>
      </section>
      <section className="panel account-section" aria-labelledby="class-setup-title">
        <div className="section-heading-row admin-section-heading">
          <div>
            <h2 id="class-setup-title">{t.schoolClasses}</h2>
            <p>{t.adminClassHelp}</p>
          </div>
        </div>
        {loading ? (
          <p role="status">{t.loading}</p>
        ) : activeTeachers.length ? (
          <form className="admin-class-form" aria-labelledby="class-setup-title" onSubmit={createClass}>
            <Field label={t.className}>
              <input name="class_name" required maxLength={80} />
            </Field>
            <Field label={t.grade}>
              <select name="grade" defaultValue="8">
                {Array.from({ length: 12 }, (_, index) => index + 1).map((grade) => (
                  <option key={grade} value={grade}>
                    {grade}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t.assignedTeacher}>
              <select name="teacher_id" required defaultValue="">
                <option value="" disabled>
                  {t.chooseTeacher}
                </option>
                {activeTeachers.map((teacher) => (
                  <option key={teacher.id} value={teacher.id}>
                    {teacher.display_name}
                  </option>
                ))}
              </select>
            </Field>
            <button className="secondary" disabled={busy}>
              {busy ? t.loading : t.createClass}
            </button>
          </form>
        ) : (
          <p className="empty-state">{t.createTeacherFirst}</p>
        )}
        {dashboard?.classes.length ? (
          <ul className="learner-list admin-class-list">
            {dashboard.classes.map((item) => (
              <li key={item.id}>
                <div className="account-details">
                  <strong>{item.name}</strong>
                  <span>
                    {t.grade} {item.grade}
                  </span>
                </div>
                <span>{item.student_count} {t.learners.toLowerCase()}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <section className="panel account-section" aria-labelledby="teacher-accounts-title">
        <div className="section-heading-row account-management-heading">
          <h2 id="teacher-accounts-title">{t.teacherAccounts}</h2>
          <Field label={t.filterAccounts}>
            <input
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              type="search"
              autoComplete="off"
            />
          </Field>
        </div>
        {loading ? (
          <p role="status">{t.loading}</p>
        ) : visibleTeachers.length ? (
          <ul className="learner-list">
            {visibleTeachers.map((teacher) => (
              <li key={teacher.id}>
                <div className="account-details">
                  <strong>{teacher.display_name}</strong>
                  <span>{teacher.username}</span>
                  <small>
                    {teacher.disabled
                      ? t.disabledAccount
                      : teacher.must_change_password
                        ? t.passwordChangeRequired
                        : t.activeAccount}
                  </small>
                </div>
                <div className="account-row-actions">
                  <button
                    className="text-button"
                    type="button"
                    disabled={busy || teacher.disabled}
                    onClick={() => void resetPassword(teacher)}
                  >
                    {t.resetPassword}
                  </button>
                  <button
                    className="text-button"
                    type="button"
                    disabled={busy}
                    onClick={() => void setTeacherDisabled(teacher, !teacher.disabled)}
                  >
                    {teacher.disabled ? t.restoreAccount : t.deactivateAccount}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">{filter ? t.noMatchingAccounts : t.noTeachers}</p>
        )}
      </section>
    </section>
  )
}
