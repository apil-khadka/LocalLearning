import { useState, type FormEvent } from 'react'
import { LockKey, UploadSimple } from '@phosphor-icons/react'
import { api, type Book, type Services } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice, Field, Status } from '../components/ui'

type IndexStatus = { services: Services; documents: Book[] }
export default function Staff({ t, refresh }: { t: Copy; refresh: () => void }) {
  const [tokenInput, setTokenInput] = useState('')
  const [token, setToken] = useState('')
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const [indexCandidateId, setIndexCandidateId] = useState('')
  const [indexSuccess, setIndexSuccess] = useState(false)
  async function login(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      setStatus(
        await api<IndexStatus>('/admin/index-status', {
          headers: { Authorization: `Bearer ${tokenInput}` },
        }),
      )
      setToken(tokenInput)
      setTokenInput('')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  async function ingest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setSuccess(false)
    const form = event.currentTarget
    try {
      await api('/admin/documents', {
        method: 'POST',
        body: new FormData(form),
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(600_000),
      })
      setSuccess(true)
      form.reset()
      refresh()
      setStatus(
        await api<IndexStatus>('/admin/index-status', {
          headers: { Authorization: `Bearer ${token}` },
        }),
      )
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  async function indexBook() {
    if (!indexCandidateId) return
    setBusy(true)
    setError(null)
    setIndexSuccess(false)
    try {
      await api<Book>('/admin/index-book', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: indexCandidateId }),
        signal: AbortSignal.timeout(600_000),
      })
      setIndexSuccess(true)
      const next = await api<IndexStatus>('/admin/index-status', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setStatus(next)
      refresh()
      const candidate = next.documents.find(
        (document) => document.index_status !== 'indexed' && document.index_status !== 'indexing',
      )
      setIndexCandidateId(candidate?.id ?? '')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  return (
    <>
      <header className="page-heading">
        <h1>{t.staff}</h1>
        <p>{t.staffIntro}</p>
      </header>
      <ErrorNotice error={error} t={t} />
      {!token ? (
        <form onSubmit={login} className="panel staff-login">
          <LockKey size={35} aria-hidden="true" />
          <Field label={t.token}>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
            />
          </Field>
          <p className="small-note">{t.privacyToken}</p>
          <button className="primary" disabled={busy}>
            {busy ? t.loading : t.login}
          </button>
        </form>
      ) : (
        <>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => {
              setToken('')
              setStatus(null)
              setError(null)
              setSuccess(false)
              setIndexSuccess(false)
            }}
          >
            {t.logout}
          </button>
          <section className="panel">
            <h2>{t.diagnostics}</h2>
            <div className="diagnostics">
              {status &&
                Object.entries(status.services.dependencies).map(([name, value]) => (
                  <div key={name}>
                    <span>{name}</span>
                    <Status value={value} t={t} />
                  </div>
                ))}
            </div>
          </section>
          <section className="panel kolibri-management">
            <h2>{t.kolibriAdmin}</h2>
            <p>{t.kolibriIntro}</p>
            <div className="kolibri-entry">
              <Status value={status?.services.kolibri.status ?? 'unconfigured'} t={t} />
              {status?.services.kolibri.url ? (
                <a
                  className="button primary button-link"
                  href={status.services.kolibri.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t.kolibriOpen}
                </a>
              ) : (
                <p className="small-note">{t.kolibriNeedsSetup}</p>
              )}
            </div>
            <details className="kolibri-workflow">
              <summary>{t.kolibriWorkflow}</summary>
              <ol>
                <li>{t.kolibriSetupStep}</li>
                <li>{t.kolibriRightsStep}</li>
                <li>{t.kolibriImportStep}</li>
                <li>{t.kolibriUpdateStep}</li>
                <li>{t.kolibriVerifyStep}</li>
              </ol>
              <p className="small-note">{t.kolibriSeparationNote}</p>
              <a
                href="https://github.com/apil-khadka/LocalLearning/blob/main/docs/KOLIBRI_GUIDE.md"
                target="_blank"
                rel="noreferrer"
              >
                {t.kolibriGuide}
              </a>
            </details>
          </section>
          <form onSubmit={ingest} className="panel">
            <h2>{t.importTitle}</h2>
            <fieldset disabled={busy}>
              <div className="form-grid">
                <Field label={t.title}>
                  <input name="title" required maxLength={120} />
                </Field>
                <Field label={t.grade}>
                  <input name="grade" type="number" min={0} max={12} defaultValue={8} required />
                </Field>
                <Field label={t.subject}>
                  <input name="subject" defaultValue="Science" required maxLength={120} />
                </Field>
                <Field label={t.chapter}>
                  <input name="chapter" required maxLength={120} />
                </Field>
                <Field label={t.license}>
                  <input name="license" required maxLength={120} />
                </Field>
                <Field label={t.source}>
                  <input name="source" required maxLength={500} />
                </Field>
              </div>
              <Field label={t.file}>
                <input type="file" name="file" accept=".pdf,.txt" required />
              </Field>
              <button className="primary">
                <UploadSimple size={19} aria-hidden="true" />
                {busy ? t.importing : t.import}
              </button>
            </fieldset>
            {success && <p role="status">{t.imported}</p>}
          </form>
          <section className="panel index-library">
            <h2>{t.indexBooksTitle}</h2>
            <p>{t.indexBooksIntro}</p>
            <div className="index-library-controls">
              <Field label={t.indexBookChoice}>
                <select
                  value={indexCandidateId}
                  disabled={busy}
                  onChange={(event) => {
                    setIndexCandidateId(event.target.value)
                    setIndexSuccess(false)
                  }}
                >
                  <option value="">{t.chooseUnindexedBook}</option>
                  {status?.documents
                    .filter(
                      (document) =>
                        !(
                          document.index_status === 'indexed' ||
                          (!document.index_status && (document.chunks ?? 0) > 0)
                        ) &&
                        document.index_status !== 'indexing' &&
                        document.index_status !== 'needs_ocr',
                    )
                    .map((document) => (
                      <option value={document.id} key={document.id}>
                        {document.grade === null
                          ? t.allGrades
                          : `${t.grade} ${document.grade || 'K'}`}{' '}
                        · {document.subject} · {document.title}
                      </option>
                    ))}
                </select>
              </Field>
              <button
                className="primary"
                disabled={busy || !indexCandidateId}
                onClick={indexBook}
                type="button"
              >
                {busy ? t.indexingBook : t.indexOneBook}
              </button>
            </div>
            {indexSuccess && <p role="status">{t.bookIndexed}</p>}
          </section>
          <section className="panel">
            <h2>{t.catalog}</h2>
            {!status?.documents.length && <p>{t.noStaffDocs}</p>}
            {status?.documents.map((doc) => (
              <p key={doc.id}>
                {doc.title} / {doc.status}
                {` / ${t.indexStatusLabel}: ${t[(doc.index_status ?? ((doc.chunks ?? 0) > 0 ? 'indexed' : 'notIndexed')) as keyof Copy]}`}
                {doc.ocr_required_pages.length > 0 &&
                  ` / ${t.ocr}: ${doc.ocr_required_pages.join(', ')}`}
              </p>
            ))}
          </section>
        </>
      )}
    </>
  )
}
