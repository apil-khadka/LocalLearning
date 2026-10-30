import { BookOpen, ChatCircleDots, GlobeHemisphereEast, PlayCircle, WifiHigh } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { Mountains, Status } from '../components/ui'
import type { Services } from '../lib/api'
import type { Copy } from '../lib/i18n'

export default function Home({ t, services }: { t: Copy; services: Services | null }) {
  const resources = [
    { title: t.tutor, description: t.tutorDescription, icon: ChatCircleDots, color: 'blue', path: '/tutor', status: services?.tutor.status },
    { title: t.books, description: t.booksDescription, icon: BookOpen, color: 'green', path: '/books', status: services?.books.status },
    { title: t.wikipedia, description: t.wikiDescription, icon: GlobeHemisphereEast, color: 'purple', url: services?.kiwix.url, status: services?.kiwix.status },
    { title: t.videos, description: t.videoDescription, icon: PlayCircle, color: 'gold', url: services?.kolibri.url, status: services?.kolibri.status },
  ]
  return <>
    <section className="hero"><div className="hero-copy"><p>{t.school}</p>
      <h1>{t.greeting}</h1><p className="intro">{t.intro}</p>
      <Link className="button primary" to="/books"><BookOpen size={20} aria-hidden="true" />{t.books}</Link>
    </div><Mountains /></section>
    <section className="resources" aria-labelledby="resources-title">
      <div className="section-heading"><div><h2 id="resources-title">{t.resources}</h2><p>{t.choose}</p></div></div>
      <div className="resource-grid">{resources.map(({ title, description, icon: Icon, color, path, url, status }) => {
        const content = <><span className={`resource-icon ${color}`}><Icon size={30} weight="duotone" aria-hidden="true" /></span>
          <h3>{title}</h3><p>{description}</p><div className="resource-bottom">{status ? <Status value={status} t={t} /> : <span className="muted">{services ? t.unavailable : t.checking}</span>}</div></>
        return path ? <Link key={title} to={path} className="resource-card">{content}</Link>
          : url ? <a key={title} href={url} className="resource-card">{content}</a>
          : <article key={title} className="resource-card resource-inactive">{content}</article>
      })}</div>
    </section>
    <aside className="network-note"><WifiHigh size={28} aria-hidden="true" /><div><h2>{t.helpTitle}</h2><p>{t.help}</p></div></aside>
  </>
}
