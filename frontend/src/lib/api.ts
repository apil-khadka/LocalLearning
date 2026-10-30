export type ResourceStatus =
  | 'ready'
  | 'reachable'
  | 'disabled'
  | 'unavailable'
  | 'unconfigured'
  | 'missing_model'
export type Services = {
  tutor: { status: ResourceStatus }
  books: { status: ResourceStatus; count: number }
  kiwix: { status: ResourceStatus; url: string | null }
  kolibri: { status: ResourceStatus; url: string | null }
  dependencies: Record<string, ResourceStatus>
}
export type Book = {
  id: string
  title: string
  grade: number
  subject: string
  chapter: string
  license: string
  source: string
  pages: number
  status: string
  ocr_required_pages: number[]
}
export type Reply = {
  answer: string
  grounding: 'textbook' | 'general'
  model: string
  sources: {
    document_id: string
    title: string
    page_start: number
    page_end: number
    chunk_id: string
  }[]
}

export class ApiError extends Error {
  constructor(
    message: string,
    public requestId: string | null,
  ) {
    super(message)
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    signal: options.signal ?? AbortSignal.timeout(180_000),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      typeof body.detail === 'string' ? body.detail : 'The request could not be completed.',
      response.headers.get('X-Request-ID'),
    )
  }
  return response.json() as Promise<T>
}
