export type ResourceStatus =
  | 'ready'
  | 'reachable'
  | 'configured'
  | 'disabled'
  | 'unavailable'
  | 'unconfigured'
  | 'missing_model'
export type Services = {
  tutor: { status: ResourceStatus }
  books: { status: ResourceStatus; count: number }
  kiwix: { status: ResourceStatus; url: string | null }
  kolibri: {
    status: ResourceStatus
    url: string | null
    version?: string | null
    channel_count?: number | null
    available_count?: number | null
    resource_count?: number | null
  }
  dependencies: Record<string, ResourceStatus>
}
export type KolibriChannel = {
  id: string
  name: string
  description: string
  version: number
  lang_code: string
  lang_name: string
  total_resources: number
  available: boolean
  learn_url: string | null
}
export type KolibriCatalog = {
  status: ResourceStatus
  url: string
  version: string | null
  channel_count?: number
  available_count?: number
  channels: KolibriChannel[]
}
export type Book = {
  id: string
  title: string
  filename?: string
  grade: number | null
  subject: string
  chapter: string
  license: string
  source: string
  pages: number
  status: string
  chunks?: number
  index_status?: 'not_indexed' | 'indexing' | 'indexed' | 'failed' | 'needs_ocr'
  ocr_required_pages: number[]
}
export type TextbookCatalog = {
  items: Book[]
  total: number
  limit: number
  offset: number
  subjects: string[]
}
export type TutorMode = 'explain' | 'hint' | 'debug'
export type AccountUser = {
  id: string
  username: string
  display_name: string
  role: 'admin' | 'teacher' | 'student'
  grade: number | null
  must_change_password: boolean
  disabled?: boolean
}
export type AuthResponse = { user: AccountUser; csrf_token: string }
export type TutorSession = {
  id: string
  student_id?: string
  student_name?: string
  username?: string
  title: string
  grade: number
  subject: string
  chapter: string
  language: 'en' | 'ne'
  mode: TutorMode
  hint_level: number
  created_at: string
  updated_at: string
  message_count: number
}
export type TutorMessage = {
  role: 'user' | 'assistant'
  content: string
  attempt: string
  mode: TutorMode | null
  grounding: Reply['grounding'] | null
  sources: Reply['sources']
  created_at: string
}
export type StudentDashboardData = {
  user: AccountUser
  classes: { id: string; name: string; grade: number }[]
  session_count: number
  recent_sessions: TutorSession[]
}
export type TeacherDashboardData = {
  user: AccountUser
  classes: {
    id: string
    name: string
    grade: number
    student_count: number
    session_count: number
  }[]
  student_count: number
  session_count: number
}
export type Reply = {
  answer: string
  grounding: 'textbook' | 'note' | 'general'
  model: string
  mode: TutorMode
  session_id: string | null
  sources: {
    document_id: string
    title: string
    page_start: number
    page_end: number
    chunk_id: string
    kind: 'passage' | 'note'
    note_id: string | null
  }[]
}
export type PageRange = { start: number; end: number }
export type NoteFields = {
  title: string
  grade: number
  subject: string
  chapter: string
  language: 'en' | 'ne'
  document_id: string
  pages: PageRange[]
  key_ideas: string[]
  worked_example: string
  misconceptions: { wrong: string; correction: string }[]
  hints: string[]
  check_question: string
  kolibri_channel_id: string | null
}
export type StudyNote = Omit<NoteFields, 'kolibri_channel_id'> & {
  id: string
  revision: number
  book_title: string
  kolibri_url: string | null
}
export type StaffNote = NoteFields & {
  id: string
  author_id: string
  status: 'draft' | 'in_review' | 'approved'
  revision: number
  reviewer: string
  reviewed_at: string | null
}
export const readerLink = (documentId: string, page?: number) =>
  `/books/${documentId}${page && page > 0 ? `?page=${page}` : ''}`

export class ApiError extends Error {
  constructor(
    message: string,
    public requestId: string | null,
  ) {
    super(message)
  }
}

let csrfToken = ''
export function setCsrfToken(value: string) {
  csrfToken = value
}

declare global {
  interface Window {
    DIGITAL_HIMALAYA_CONFIG?: { publicPort?: number; staffPort?: number }
  }
}

function configuredPorts() {
  const publicPort = window.DIGITAL_HIMALAYA_CONFIG?.publicPort
  const staffPort = window.DIGITAL_HIMALAYA_CONFIG?.staffPort
  if (
    Number.isInteger(publicPort) &&
    Number.isInteger(staffPort) &&
    Number(publicPort) > 0 &&
    Number(publicPort) <= 65535 &&
    Number(staffPort) > 0 &&
    Number(staffPort) <= 65535
  ) {
    return { publicPort: String(publicPort), staffPort: String(staffPort) }
  }
  return null
}

export function isStudentListener() {
  const ports = configuredPorts()
  if (ports) {
    const currentPort =
      window.location.port || (window.location.protocol === 'https:' ? '443' : '80')
    return currentPort === ports.publicPort
  }
  return ['8090', '18090'].includes(window.location.port)
}

export function staffPortalUrl(path = '/staff') {
  const url = new URL(window.location.href)
  const ports = configuredPorts()
  if (ports) {
    const currentPort = url.port || (url.protocol === 'https:' ? '443' : '80')
    if (currentPort === ports.publicPort) url.port = ports.staffPort
  } else {
    if (url.port === '8090' || url.port === '8091') url.port = '8091'
    if (url.port === '18090' || url.port === '18091') url.port = '18091'
  }
  url.pathname = path
  url.search = ''
  url.hash = ''
  return url.toString()
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken && !headers.has('X-CSRF-Token')) {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const response = await fetch(`/api${path}`, {
    ...options,
    headers,
    credentials: 'same-origin',
    signal: options.signal ?? AbortSignal.timeout(180_000),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      typeof body.detail === 'string' ? body.detail : 'The request could not be completed.',
      response.headers.get('X-Request-ID'),
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
