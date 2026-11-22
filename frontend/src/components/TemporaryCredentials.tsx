import { useState } from 'react'
import type { Copy } from '../lib/i18n'

export type TemporaryCredentialsData = {
  displayName: string
  username: string
  password: string
}

export default function TemporaryCredentials({
  t,
  credentials,
  onDismiss,
  onCopyError,
}: {
  t: Copy
  credentials: TemporaryCredentialsData
  onDismiss: () => void
  onCopyError: (error: unknown) => void
}) {
  const [copied, setCopied] = useState(false)

  async function copyCredentials() {
    try {
      if (!navigator.clipboard) throw new Error(t.clipboardUnavailable)
      await navigator.clipboard.writeText(
        `${t.displayName}: ${credentials.displayName}\n${t.username}: ${credentials.username}\n${t.password}: ${credentials.password}`,
      )
      setCopied(true)
    } catch (error) {
      onCopyError(error)
    }
  }

  return (
    <section className="credential-reveal" aria-labelledby="credential-title">
      <div className="credential-heading">
        <div>
          <h2 id="credential-title">{t.signInDetails}</h2>
          <p>{credentials.displayName}</p>
        </div>
        <button className="text-button" type="button" onClick={onDismiss}>
          {t.dismissCredentials}
        </button>
      </div>
      <dl className="credential-values">
        <div>
          <dt>{t.username}</dt>
          <dd>
            <code>{credentials.username}</code>
          </dd>
        </div>
        <div>
          <dt>{t.temporaryPassword}</dt>
          <dd>
            <code className="temporary-credential">{credentials.password}</code>
          </dd>
        </div>
      </dl>
      <p className="small-note">{t.credentialSharingHelp}</p>
      <div className="credential-actions">
        <button className="secondary" type="button" onClick={() => void copyCredentials()}>
          {t.copyCredentials}
        </button>
        {copied && (
          <span className="success-note" role="status">
            {t.credentialsCopied}
          </span>
        )}
      </div>
    </section>
  )
}
