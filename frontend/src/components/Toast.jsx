function CheckIcon() {
  return (
    <svg className="mt-0.5 h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.25" />
      <path d="m8.25 12.4 2.5 2.5 5-5.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ErrorIcon() {
  return (
    <svg className="mt-0.5 h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.25" />
      <path d="M12 7.5v5.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="12" cy="16.4" r="1.3" fill="currentColor" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m6.5 6.5 11 11m0-11-11 11" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

// Floating notification card rendered top-center (fixed), so it is always
// visible without scrolling — including on small mobile screens.
export default function Toast({ toasts, onClose }) {
  if (!toasts.length) return null
  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[100] flex flex-col items-center gap-2 px-4" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast-card pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-[0_14px_40px_rgba(0,0,0,0.22)] ring-1 ${
            toast.type === 'error' ? 'bg-red-600 ring-red-400/50' : 'bg-emerald-600 ring-emerald-400/50'
          }`}
        >
          {toast.type === 'error' ? <ErrorIcon /> : <CheckIcon />}
          <p className="flex-1 leading-snug">{toast.message}</p>
          <button
            type="button"
            onClick={() => onClose(toast.id)}
            className="ml-1 mt-0.5 shrink-0 rounded-md p-0.5 opacity-75 transition hover:opacity-100"
            aria-label="Dismiss notification"
          >
            <CloseIcon />
          </button>
        </div>
      ))}
    </div>
  )
}
