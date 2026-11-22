import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setCsrfToken, type AccountUser, type AuthResponse } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field } from '../components/ui'

export default function ChangePassword({
  t,
  onAuthenticated,
}: {
  t: Copy
  onAuthenticated: (user: AccountUser) => void
}) {
  const navigate = useNavigate()
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const next = String(form.get('new_password') ?? '')
    if (next !== String(form.get('confirm_password') ?? '')) {
      setError(new Error(t.passwordsDoNotMatch))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await api<AuthResponse>('/auth/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: form.get('current_password'),
          new_password: next,
        }),
      })
      setCsrfToken(result.csrf_token)
      onAuthenticated(result.user)
      navigate(
        result.user.role === 'student'
          ? '/dashboard'
          : result.user.role === 'admin'
            ? '/admin'
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
        <h1>{t.changePassword}</h1>
        <p>{t.changePasswordIntro}</p>
      </header>
      <form className="panel account-form" onSubmit={submit}>
        <Field label={t.currentPassword}>
          <input name="current_password" type="password" required autoComplete="current-password" />
        </Field>
        <Field label={t.newPassword}>
          <input
            name="new_password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete="new-password"
          />
        </Field>
        <Field label={t.confirmPassword}>
          <input
            name="confirm_password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete="new-password"
          />
        </Field>
        <ErrorNotice error={error} t={t} />
        <button className="primary" disabled={busy}>
          {busy ? t.loading : t.changePassword}
        </button>
      </form>
    </section>
  )
}
