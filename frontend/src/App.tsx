import { useCallback, useEffect, useState } from 'react'
import {
  BookBookmark,
  BookOpen,
  ChatCircleDots,
  House,
  PlayCircle,
  SignOut,
  WifiHigh,
  UserCircle,
} from '@phosphor-icons/react'
import * as ToggleGroup from '@radix-ui/react-toggle-group'
import { Link, NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api, setCsrfToken, type AccountUser, type Services } from './lib/api'
import { copy, type Language } from './lib/i18n'
import Home from './pages/Home'
import Tutor from './pages/Tutor'
import Books from './pages/Books'
import BookReader from './pages/BookReader'
import Courses from './pages/Courses'
import Study from './pages/Study'
import Staff from './pages/Staff'
import Login from './pages/Login'
import TeacherDashboard from './pages/TeacherDashboard'
import AdminDashboard from './pages/AdminDashboard'
import { SessionHistory, StudentDashboard } from './pages/Dashboard'
import ChangePassword from './pages/ChangePassword'

export default function App() {
  const navigate = useNavigate()
  const [language, setLanguage] = useState<Language>('en')
  const [services, setServices] = useState<Services | null>(null)
  const [connection, setConnection] = useState<'checking' | 'connected' | 'disconnected'>(
    'checking',
  )
  const [account, setAccount] = useState<AccountUser | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [authReady, setAuthReady] = useState(false)
  const t = copy[language]
  const accountPath =
    account?.role === 'admin' ? '/admin' : account?.role === 'teacher' ? '/teacher' : '/dashboard'
  const accountLabel =
    account?.role === 'admin'
      ? t.adminDashboard
      : account?.role === 'teacher'
        ? t.teacherDashboard
        : t.dashboard
  const accountShortLabel =
    account?.role === 'admin'
      ? t.adminShort
      : account?.role === 'teacher'
        ? t.teacherShort
        : t.dashboardShort
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
    Promise.all([
      api<{ authentication_required: boolean }>('/auth/status').catch(() => null),
      api<{ user: AccountUser; csrf_token: string }>('/auth/me').catch(() => null),
    ]).then(([status, auth]) => {
      setAuthRequired(status?.authentication_required ?? false)
      if (auth) {
        setCsrfToken(auth.csrf_token)
        setAccount(auth.user)
        if (auth.user.must_change_password) navigate('/change-password', { replace: true })
      }
      setAuthReady(true)
    })
  }, [navigate])
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
          <div className="topbar-inner">
            <Link className="topbar-brand" to="/" aria-label={`Digital Himalaya - ${t.home}`}>
              <span className="topbar-mark">
                <img src="/brand/digital-himalaya-mark.png" width="28" height="28" alt="" />
              </span>
              <span className="topbar-brand-name">
                <span className="brand-full">Digital Himalaya</span>
                <span className="brand-short">Himalaya</span>
              </span>
              <span
                className={`topbar-status-dot ${connection}`}
                title={t[connection]}
                aria-hidden="true"
              />
            </Link>
            <nav id="primary-navigation" className="primary-navigation" aria-label={t.mainNavigation}>
              <NavLink to="/" end aria-label={t.home}>
                <House size={19} aria-hidden="true" />
                <span className="nav-label-full">{t.homeShort}</span>
                <span className="nav-label-short">{t.homeShort}</span>
              </NavLink>
              <NavLink to="/tutor" aria-label={t.tutor}>
                <ChatCircleDots size={19} aria-hidden="true" />
                <span className="nav-label-full">{t.tutor}</span>
                <span className="nav-label-short">{t.tutorShort}</span>
              </NavLink>
              <NavLink to="/books" aria-label={t.books}>
                <BookOpen size={19} aria-hidden="true" />
                <span className="nav-label-full">{t.books}</span>
                <span className="nav-label-short">{t.booksShort}</span>
              </NavLink>
              <NavLink to="/study" aria-label={t.study}>
                <BookBookmark size={19} aria-hidden="true" />
                <span className="nav-label-full">{t.study}</span>
                <span className="nav-label-short">{t.studyShort}</span>
              </NavLink>
              <NavLink to="/courses" aria-label={t.courses}>
                <PlayCircle size={19} aria-hidden="true" />
                <span className="nav-label-full">{t.courses}</span>
                <span className="nav-label-short">{t.coursesShort}</span>
              </NavLink>
            </nav>
            <div className="topbar-utilities">
              <ToggleGroup.Root
                type="single"
                value={language}
                onValueChange={(value) => {
                  if (value === 'en' || value === 'ne') setLanguage(value)
                }}
                aria-label="Language / भाषा"
                className="language-toggle topbar-language"
              >
                <ToggleGroup.Item value="en" lang="en" aria-label="English">
                  {t.langEnShort}
                </ToggleGroup.Item>
                <ToggleGroup.Item value="ne" lang="ne">
                  {t.langNeShort}
                </ToggleGroup.Item>
              </ToggleGroup.Root>
              {!account ? (
                <NavLink to="/login" className="topbar-signin" aria-label={t.signIn}>
                  <UserCircle size={18} aria-hidden="true" />
                  <span>{t.signIn}</span>
                </NavLink>
              ) : (
                <div className="topbar-account">
                  <NavLink to={accountPath} className="topbar-account-link" aria-label={accountLabel}>
                    <UserCircle size={18} aria-hidden="true" />
                    <span className="account-label-full">{accountShortLabel}</span>
                    <span className="account-label-short">{t.account}</span>
                  </NavLink>
                  <button
                    type="button"
                    className="account-signout"
                    aria-label={t.signOut}
                    onClick={async () => {
                      try {
                        await api('/auth/logout', { method: 'POST' })
                      } finally {
                        setCsrfToken('')
                        setAccount(null)
                        navigate('/')
                      }
                    }}
                  >
                    <SignOut size={17} aria-hidden="true" />
                    <span className="signout-label">{t.signOut}</span>
                  </button>
                </div>
              )}
            </div>
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
              element={
                <Tutor
                  t={t}
                  language={language}
                  services={services}
                  account={account}
                  authReady={authReady}
                  authRequired={authRequired}
                />
              }
            />
            <Route path="/books" element={<Books t={t} />} />
            <Route path="/books/:id" element={<BookReader t={t} />} />
            <Route path="/study" element={<Study t={t} />} />
            <Route path="/courses" element={<Courses t={t} />} />
            <Route
              path="/staff"
              element={<Staff t={t} refresh={refresh} account={account} authReady={authReady} />}
            />
            <Route
              path="/login"
              element={
                authReady && account ? (
                  <Navigate to={accountPath} replace />
                ) : (
                  <Login t={t} onAuthenticated={setAccount} />
                )
              }
            />
            <Route
              path="/dashboard"
              element={
                !authReady ? null : account?.must_change_password ? (
                  <Navigate to="/change-password" replace />
                ) : account?.role === 'student' ? (
                  <StudentDashboard t={t} />
                ) : (
                  <Navigate
                    to={account ? (account.role === 'admin' ? '/admin' : '/teacher') : '/login'}
                    replace
                  />
                )
              }
            />
            <Route
              path="/teacher"
              element={
                !authReady ? null : account?.must_change_password ? (
                  <Navigate to="/change-password" replace />
                ) : account?.role === 'teacher' ? (
                  <TeacherDashboard t={t} />
                ) : (
                  <Navigate
                    to={account ? (account.role === 'admin' ? '/admin' : '/dashboard') : '/login'}
                    replace
                  />
                )
              }
            />
            <Route
              path="/admin"
              element={
                !authReady ? null : account?.must_change_password ? (
                  <Navigate to="/change-password" replace />
                ) : account?.role === 'admin' ? (
                  <AdminDashboard t={t} />
                ) : (
                  <Navigate
                    to={account ? (account.role === 'teacher' ? '/teacher' : '/dashboard') : '/login'}
                    replace
                  />
                )
              }
            />
            <Route
              path="/history"
              element={
                !authReady ? null : account ? (
                  <SessionHistory t={t} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/change-password"
              element={
                !authReady ? null : account ? (
                  <ChangePassword t={t} onAuthenticated={setAccount} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
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
          <div className="footer-meta">
            <Link className="footer-brand" to="/" aria-label={`Digital Himalaya - ${t.home}`}>
              <img src="/brand/digital-himalaya-mark.png" width="44" height="44" alt="" />
              <span>Himalaya</span>
            </Link>
            <span className={`connection ${connection}`} aria-label={t[connection]}>
              <WifiHigh size={19} aria-hidden="true" />
              <span className="connection-label">{t[connection]}</span>
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
