import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  isStudentListener,
  setCsrfToken,
  staffPortalUrl,
  type AccountUser,
  type AuthResponse,
} from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

type AuthStatus = { users_exist: boolean; authentication_required: boolean }

export default function Login({
  t,
  onAuthenticated,
}: {
  t: Copy
  onAuthenticated: (user: AccountUser) => void
}) {
  const navigate = useNavigate()
  const [status, setStatus] = useState<AuthStatus | null>(null)
  const [setup, setSetup] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => {
    api<AuthStatus>('/auth/status')
      .then((value) => {
        setStatus(value)
        setSetup(!value.users_exist)
      })
      .catch(setError)
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError(null)
    try {
      const headers = new Headers({ 'Content-Type': 'application/json' })
      if (setup) headers.set('Authorization', `Bearer ${String(form.get('token') ?? '')}`)
      const result = await api<AuthResponse>(setup ? '/auth/bootstrap' : '/auth/login', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          username: form.get('username'),
          password: form.get('password'),
          ...(setup ? { display_name: form.get('display_name') } : {}),
        }),
      })
      setCsrfToken(result.csrf_token)
      onAuthenticated(result.user)
      if (result.user.role !== 'student' && isStudentListener()) {
        window.location.assign(staffPortalUrl('/teacher'))
        return
      }
      navigate(
        result.user.must_change_password
          ? '/change-password'
          : result.user.role === 'student'
            ? '/dashboard'
            : '/teacher',
        { replace: true },
      )
    } catch (cause) {
      setError(cause)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="account-page">
      <header className="page-heading">
        <h1>{setup ? t.setupAdmin : t.signIn}</h1>
        <p>{setup ? t.setupAdminHelp : t.account}</p>
      </header>
      <form className="panel account-form" onSubmit={submit}>
        {setup && (
          <>
            <Field label={t.setupToken}>
              <input name="token" type="password" required autoComplete="off" />
            </Field>
            <Field label={t.displayName}>
              <input name="display_name" required maxLength={80} autoComplete="name" />
            </Field>
          </>
        )}
        <Field label={t.username}>
          <input name="username" required minLength={3} maxLength={48} autoComplete="username" />
        </Field>
        <Field label={t.password}>
          <input
            name="password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete={setup ? 'new-password' : 'current-password'}
          />
        </Field>
        <ErrorNotice error={error} t={t} />
        <button className="primary" disabled={busy || !status}>
          {busy ? t.loading : setup ? t.setupAdmin : t.signIn}
        </button>
        {setup && status?.users_exist && (
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setSetup(false)
              setError(null)
            }}
          >
            {t.signIn}
          </button>
        )}
      </form>
    </section>
  )
}
