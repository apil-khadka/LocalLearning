import { useEffect, useState } from 'react'
import { ArrowSquareOut, PlayCircle } from '@phosphor-icons/react'
import { api, type KolibriCatalog } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice } from '../components/ui'

export default function Courses({ t }: { t: Copy }) {
  const [catalog, setCatalog] = useState<KolibriCatalog | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const availableCount =
    catalog?.channels.filter(
      (channel) => channel.available && channel.total_resources > 0 && channel.learn_url,
    ).length ?? 0

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    api<KolibriCatalog>('/kolibri/channels', { signal: controller.signal })
      .then(setCatalog)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [attempt])

  return (
    <>
      <header className="page-heading">
        <h1>{t.courses}</h1>
        <p>{t.coursesIntro}</p>
      </header>
      <ErrorNotice error={error} t={t} />
      {loading ? (
        <div className="catalog-loading" role="status">
          <span />
          <span />
          <span />
          <span />
        </div>
      ) : error || !catalog ? (
        <div className="empty-state">
          <PlayCircle size={45} aria-hidden="true" />
          <h2>{t.coursesUnavailable}</h2>
          <p>{t.help}</p>
          <button className="secondary" onClick={() => setAttempt((value) => value + 1)}>
            {t.retry}
          </button>
        </div>
      ) : (
        <>
          <div className="catalog-toolbar">
            <div className="catalog-count" aria-live="polite">
              {availableCount}/{catalog.channels.length} {t.kolibriChannelCounts}
              {catalog.version ? (
                <>
                  {' '}
                  <span aria-hidden="true">·</span> {t.kolibriVersion} {catalog.version}
                </>
              ) : null}
            </div>
            <div className="catalog-actions">
              <a
                className="button primary button-link"
                href={catalog.url}
                target="_blank"
                rel="noreferrer"
              >
                {t.openKolibriLibrary}
              </a>
            </div>
          </div>
          {catalog.channels.length === 0 ? (
            <div className="empty-state">
              <PlayCircle size={45} aria-hidden="true" />
              <h2>{t.coursesEmpty}</h2>
              <p>{t.coursesEmptyNote}</p>
            </div>
          ) : (
            <div className="catalog-layout">
              <section className="catalog-results" aria-label={t.courses}>
                {catalog.channels.map((channel) => {
                  const ready =
                    channel.available && channel.total_resources > 0 && channel.learn_url
                  const content = (
                    <>
                      <span className="catalog-book-icon">
                        <PlayCircle size={21} aria-hidden="true" />
                      </span>
                      <span className="catalog-book-copy">
                        <span className="catalog-book-meta">
                          {channel.lang_name || channel.lang_code}
                          <span aria-hidden="true"> · </span>
                          {channel.available && channel.total_resources > 0
                            ? `${channel.total_resources} ${t.channelResources}`
                            : t.channelMetadataOnly}
                        </span>
                        <span className="catalog-book-title" role="heading" aria-level={2}>
                          {channel.name}
                        </span>
                        {channel.description ? (
                          <span className="catalog-book-subtitle">{channel.description}</span>
                        ) : null}
                      </span>
                      {ready && (
                        <ArrowSquareOut
                          className="catalog-book-arrow"
                          size={18}
                          aria-hidden="true"
                        />
                      )}
                    </>
                  )
                  return (
                    <article className="catalog-book catalog-book-single" key={channel.id}>
                      {ready ? (
                        <a
                          className="catalog-book-main"
                          href={channel.learn_url!}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`${t.openChannel}: ${channel.name}`}
                        >
                          {content}
                        </a>
                      ) : (
                        <div
                          className="catalog-book-main catalog-book-unavailable"
                          aria-disabled="true"
                          aria-label={`${channel.name}: ${t.channelMetadataOnly}`}
                        >
                          {content}
                        </div>
                      )}
                    </article>
                  )
                })}
              </section>
            </div>
          )}
        </>
      )}
    </>
  )
}
