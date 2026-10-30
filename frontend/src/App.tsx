import { useCallback, useEffect, useState } from 'react'
import { BookOpen, ChatCircleDots, House, SidebarSimple, WifiHigh } from '@phosphor-icons/react'
import * as ToggleGroup from '@radix-ui/react-toggle-group'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { api, type Services } from './lib/api'
import { copy, type Language } from './lib/i18n'
import Home from './pages/Home'
import Tutor from './pages/Tutor'
import Books from './pages/Books'
import Staff from './pages/Staff'

const SIDEBAR_PREFERENCE_KEY = 'digital-himalaya-sidebar-collapsed'

function readSidebarPreference() {
  try {
    return window.localStorage.getItem(SIDEBAR_PREFERENCE_KEY) === 'true'
  } catch {
    return false
  }
}

export default function App() {
  const [language, setLanguage] = useState<Language>('en')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarPreference)
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
  const toggleSidebar = () => {
    const nextCollapsed = !sidebarCollapsed
    setSidebarCollapsed(nextCollapsed)
    try {
      window.localStorage.setItem(SIDEBAR_PREFERENCE_KEY, String(nextCollapsed))
    } catch {
      // The sidebar remains usable for this page when storage is unavailable.
    }
  }
  return (
    <div className={`app-shell${sidebarCollapsed ? ' is-sidebar-collapsed' : ''}`}>
      <a className="skip-link" href="#main">
        {t.resources}
      </a>
      <aside className="sidebar">
        <div className="sidebar-head">
          <Link
            className="brand"
            to="/"
            aria-label={`Digital Himalaya - ${t.home}`}
            title={sidebarCollapsed ? 'Digital Himalaya' : undefined}
          >
            <span className="brand-label">Himalaya</span>
          </Link>
          <button
            type="button"
            className="sidebar-toggle"
            aria-label={sidebarCollapsed ? t.expandSidebar : t.collapseSidebar}
            aria-controls="primary-navigation"
            aria-pressed={sidebarCollapsed}
            title={sidebarCollapsed ? t.expandSidebar : t.collapseSidebar}
            onClick={toggleSidebar}
          >
            <SidebarSimple size={21} weight="bold" aria-hidden="true" />
          </button>
        </div>
        <nav id="primary-navigation" className="sidebar-nav" aria-label={t.resources}>
          <NavLink
            to="/"
            end
            aria-label={t.home}
            title={sidebarCollapsed ? t.home : undefined}
            data-tooltip={sidebarCollapsed ? t.home : undefined}
          >
            <House size={23} aria-hidden="true" />
            <span className="nav-label">{t.home}</span>
          </NavLink>
          <NavLink
            to="/tutor"
            aria-label={t.tutor}
            title={sidebarCollapsed ? t.tutor : undefined}
            data-tooltip={sidebarCollapsed ? t.tutor : undefined}
          >
            <ChatCircleDots size={23} aria-hidden="true" />
            <span className="nav-label">{t.tutor}</span>
          </NavLink>
          <NavLink
            to="/books"
            aria-label={t.books}
            title={sidebarCollapsed ? t.books : undefined}
            data-tooltip={sidebarCollapsed ? t.books : undefined}
          >
            <BookOpen size={23} aria-hidden="true" />
            <span className="nav-label">{t.books}</span>
          </NavLink>
        </nav>
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
