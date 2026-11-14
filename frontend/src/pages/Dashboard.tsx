import { useEffect, useState } from 'react'
import { BookOpen, ChatCircleDots } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { api, type StudentDashboardData, type TutorSession } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { ErrorNotice } from '../components/ui'

function SessionList({
  sessions,
  t,
  onDelete,
}: {
  sessions: TutorSession[]
  t: Copy
  onDelete?: (id: string) => void
}) {
  if (!sessions.length) return <p className="empty-state">{t.noSessions}</p>
  return (
    <div className="account-session-list">
      {sessions.map((session) => (
        <article className="account-session" key={session.id}>
          <div>
            <h3>{session.title}</h3>
            <p>
              {t.grade} {session.grade} · {session.subject}
              {session.chapter ? ` · ${session.chapter}` : ''}
            </p>
            <small>{new Date(session.updated_at).toLocaleString()}</small>
          </div>
          <div className="account-session-actions">
            <Link className="secondary" to={`/tutor?session=${session.id}`}>
              {t.resumeSession}
            </Link>
            {onDelete && (
              <button className="text-button" onClick={() => onDelete(session.id)}>
                {t.deleteSession}
              </button>
            )}
          </div>
        </article>
      ))}
    </div>
  )
}

export function StudentDashboard({ t }: { t: Copy }) {
  const [data, setData] = useState<StudentDashboardData | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [sessions, setSessions] = useState<TutorSession[]>([])
  useEffect(() => {
    api<StudentDashboardData>('/student/dashboard')
      .then((result) => {
        setData(result)
        setSessions(result.recent_sessions)
      })
      .catch(setError)
  }, [])

  async function remove(id: string) {
    try {
      await api(`/account/sessions/${id}`, { method: 'DELETE' })
      setSessions((current) => current.filter((session) => session.id !== id))
      setData((current) =>
        current ? { ...current, session_count: Math.max(0, current.session_count - 1) } : current,
      )
    } catch (cause) {
      setError(cause)
    }
  }

  return (
    <section className="account-page">
      <header className="page-heading">
        <h1>{t.dashboard}</h1>
        <p>{data?.user.display_name ? `${t.welcomeBack}, ${data.user.display_name}` : t.loading}</p>
      </header>
      <ErrorNotice error={error} t={t} />
      <section className="dashboard-welcome">
        <div>
          <span>{t.continueLearning}</span>
          <h2>{sessions[0]?.title ?? t.readyForNextQuestion}</h2>
          <p>
            {sessions[0]
              ? `${t.grade} ${sessions[0].grade} · ${sessions[0].subject}`
              : t.dashboardIntro}
          </p>
        </div>
        {sessions[0] ? (
          <Link className="primary button-link" to={`/tutor?session=${sessions[0].id}`}>
            <ChatCircleDots size={18} aria-hidden="true" /> {t.resumeSession}
          </Link>
        ) : (
          <Link className="primary button-link" to="/tutor">
            <BookOpen size={18} aria-hidden="true" /> {t.tutor}
          </Link>
        )}
      </section>
      <div className="dashboard-context-row">
        <span>
          <strong>{data?.session_count ?? 0}</strong> {t.tutorSessions.toLowerCase()}
        </span>
        <span>
          <strong>{data?.classes.length ?? 0}</strong> {t.assignedClasses.toLowerCase()}
        </span>
        {data?.classes.map((item) => (
          <span className="class-context" key={item.id}>
            {item.name} · {t.grade} {item.grade}
          </span>
        ))}
      </div>
      <section className="panel account-section">
        <div className="section-heading-row">
          <h2>{t.recentSessions}</h2>
          <Link to="/history">{t.allSessions}</Link>
        </div>
        {sessions.length > 1 ? (
          <SessionList sessions={sessions.slice(1)} t={t} onDelete={remove} />
        ) : (
          <p className="empty-state">{t.noEarlierSessions}</p>
        )}
      </section>
    </section>
  )
}

export function SessionHistory({ t }: { t: Copy }) {
  const [sessions, setSessions] = useState<TutorSession[]>([])
  const [error, setError] = useState<unknown>(null)
  useEffect(() => {
    api<TutorSession[]>('/account/sessions').then(setSessions).catch(setError)
  }, [])
  async function remove(id: string) {
    try {
      await api(`/account/sessions/${id}`, { method: 'DELETE' })
      setSessions((current) => current.filter((session) => session.id !== id))
    } catch (cause) {
      setError(cause)
    }
  }
  return (
    <section className="account-page">
      <header className="page-heading">
        <h1>{t.allSessions}</h1>
      </header>
      <ErrorNotice error={error} t={t} />
      <section className="panel account-section">
        <SessionList sessions={sessions} t={t} onDelete={remove} />
      </section>
    </section>
  )
}
