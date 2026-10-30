import { useCallback, useEffect, useState } from 'react'
import {
  BookOpen,
  ChatCircleDots,
  House,
  Mountains as MountainIcon,
  WifiHigh,
} from '@phosphor-icons/react'
import * as ToggleGroup from '@radix-ui/react-toggle-group'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { api, type Services } from './lib/api'
import { copy, type Language } from './lib/i18n'
import Home from './pages/Home'
import Tutor from './pages/Tutor'
import Books from './pages/Books'
import Staff from './pages/Staff'

export default function App() {
  const [language, setLanguage] = useState<Language>('en')
  const [services, setServices] = useState<Services | null>(null)
  const [connection, setConnection] = useState<'checking' | 'connected' | 'disconnected'>(
    'checking',
  )
  const t = copy[language]
  const refresh = useCallback(() => {
    api<Services>('/services', { signal: AbortSignal.timeout(12_000) })
      .then((value) => {
        setServices(value)
        setConnection('connected')
      })
      .catch(() => {
        setServices(null)
        setConnection('disconnected')
      })
  }, [])
  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 30_000)
    return () => clearInterval(timer)
  }, [refresh])
  useEffect(() => {
    document.documentElement.lang = language
  }, [language])
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        {t.resources}
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/">
          <MountainIcon weight="duotone" size={37} aria-hidden="true" />
          <span>
            Digital
            <br />
            <strong>Himalaya</strong>
          </span>
        </Link>
        <nav aria-label={t.resources}>
          <NavLink to="/" end>
            <House size={23} aria-hidden="true" />
            {t.home}
          </NavLink>
          <NavLink to="/tutor">
            <ChatCircleDots size={23} aria-hidden="true" />
            {t.tutor}
          </NavLink>
          <NavLink to="/books">
            <BookOpen size={23} aria-hidden="true" />
            {t.books}
          </NavLink>
        </nav>
        <div className="sidebar-note">
          <MountainIcon size={32} aria-hidden="true" />
          <p>{t.localNote}</p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className={`connection ${connection}`}>
            <WifiHigh size={19} aria-hidden="true" />
            {t[connection]}
          </span>
          <ToggleGroup.Root
            type="single"
            value={language}
            onValueChange={(value) => {
              if (value === 'en' || value === 'ne') setLanguage(value)
            }}
            aria-label="Language / भाषा"
            className="language-toggle"
          >
            <ToggleGroup.Item value="en" lang="en">
              English
            </ToggleGroup.Item>
            <ToggleGroup.Item value="ne" lang="ne">
              नेपाली
            </ToggleGroup.Item>
          </ToggleGroup.Root>
        </header>
        {connection === 'disconnected' && (
          <div className="connection-error" role="alert">
            {t.error} <button onClick={refresh}>{t.retry}</button>
          </div>
        )}
        <main id="main">
          <Routes>
            <Route path="/" element={<Home t={t} services={services} />} />
            <Route
              path="/tutor"
              element={<Tutor t={t} language={language} services={services} />}
            />
            <Route path="/books" element={<Books t={t} />} />
            <Route path="/staff" element={<Staff t={t} refresh={refresh} />} />
            <Route
              path="*"
              element={
                <>
                  <h1>{t.notFound}</h1>
                  <Link to="/">{t.back}</Link>
                </>
              }
            />
          </Routes>
        </main>
        <footer>
          <span>{t.localNote}</span>
          <span>{t.connectionNote}</span>
        </footer>
      </div>
    </div>
  )
}
