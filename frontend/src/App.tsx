import { useCallback, useEffect, useState } from 'react'
import { BookOpen, ChatCircleDots, House, WifiHigh } from '@phosphor-icons/react'
import * as ToggleGroup from '@radix-ui/react-toggle-group'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { api, type Services } from './lib/api'
import { copy, type Language } from './lib/i18n'
import Home from './pages/Home'
import Tutor from './pages/Tutor'
import Books from './pages/Books'
import BookReader from './pages/BookReader'
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
      <div className="workspace">
        <header className="topbar">
          <Link className="topbar-brand" to="/" aria-label={`Digital Himalaya - ${t.home}`}>
            Himalaya
          </Link>
          <nav id="primary-navigation" className="primary-navigation" aria-label={t.mainNavigation}>
            <NavLink to="/" end aria-label={t.home}>
              <House size={21} aria-hidden="true" />
              <span className="nav-label-full">{t.home}</span>
              <span className="nav-label-short">{t.homeShort}</span>
            </NavLink>
            <NavLink to="/tutor" aria-label={t.tutor}>
              <ChatCircleDots size={21} aria-hidden="true" />
              <span className="nav-label-full">{t.tutor}</span>
              <span className="nav-label-short">{t.tutorShort}</span>
            </NavLink>
            <NavLink to="/books" aria-label={t.books}>
              <BookOpen size={21} aria-hidden="true" />
              <span className="nav-label-full">{t.books}</span>
              <span className="nav-label-short">{t.booksShort}</span>
            </NavLink>
          </nav>
          <div className="topbar-tools">
            <span className={`connection ${connection}`} aria-label={t[connection]}>
              <WifiHigh size={19} aria-hidden="true" />
              <span className="connection-label">{t[connection]}</span>
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
          </div>
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
            <Route path="/books/:id" element={<BookReader t={t} />} />
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
        <footer className="app-footer">
          <div className="footer-brand">
            <img src="/brand/digital-himalaya-mark.png" width="44" height="44" alt="" />
            <span>
              Digital <strong>Himalaya</strong>
            </span>
          </div>
          <div className="footer-details">
            <span>{t.localNote}</span>
            <span>{t.connectionNote}</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
