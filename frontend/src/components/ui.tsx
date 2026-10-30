import { WarningCircle } from '@phosphor-icons/react'
import { ApiError, type ResourceStatus } from '../lib/api'
import type { Copy } from '../lib/i18n'
import { cloneElement, isValidElement, useId, type ReactNode } from 'react'

export function Status({ value, t }: { value: ResourceStatus; t: Copy }) {
  return (
    <span className={`status status-${value}`}>
      <span aria-hidden="true" />
      {t[value]}
    </span>
  )
}

export function ErrorNotice({ error, t }: { error: unknown; t: Copy }) {
  if (!error) return null
  return (
    <div className="notice error" role="alert">
      <WarningCircle size={23} aria-hidden="true" />
      <div>
        {error instanceof ApiError ? error.message : t.error}
        {error instanceof ApiError && error.requestId && (
          <small>
            {t.report} {error.requestId}
          </small>
        )}
      </div>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  const generatedId = useId()
  const control = isValidElement<{ id?: string }>(children) ? children : null
  const id = control?.props.id ?? generatedId
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {control ? cloneElement(control, { id }) : children}
    </div>
  )
}

export function Mountains() {
  return (
    <svg className="mountains" viewBox="0 0 620 340" fill="none" aria-hidden="true">
      <circle cx="445" cy="74" r="33" fill="var(--sun)" />
      <path d="M50 340 247 70l94 129 65-111 214 252Z" fill="#c7ddcf" />
      <path d="m247 70-54 74 47-14 32 35 24-28Z" fill="#f8fcf8" />
      <path d="m406 88-38 65 35-18 25 28 20-20Z" fill="#f8fcf8" />
      <path d="M0 340 153 189l122 151Zm198 0 159-169 165 169Z" fill="#91b9a5" />
      <path d="m357 171-50 54 47-14 20 20 18-24Z" fill="#e9f2eb" />
      <path d="M0 340c123-73 188-45 287-2 110-111 210-93 333-36v38Z" fill="#568f7d" />
      <path d="M0 340c141-28 182-18 296 0 96-32 227-28 324-12v12Z" fill="#2d7667" />
    </svg>
  )
}
