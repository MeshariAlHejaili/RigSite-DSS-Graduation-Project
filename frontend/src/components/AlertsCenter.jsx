import { useState } from 'react'

const TABS = [
  { id: 'all', label: 'All' },
  { id: 'kicks', label: 'Kicks' },
  { id: 'losses', label: 'Losses' },
]

function AlertsCenter({ onBack }) {
  const [filter, setFilter] = useState('all')

  return (
    <div
      className="fixed inset-0 z-[100] flex min-h-0 flex-col bg-gradient-to-b from-slate-950 via-[#0f0d1f] to-violet-950 text-slate-100"
      role="dialog"
      aria-modal="true"
      aria-labelledby="alerts-center-title"
    >
      <header className="relative z-10 flex h-14 shrink-0 items-center justify-center border-b border-white/[0.08] bg-slate-950/80 px-4 shadow-[0_8px_32px_rgba(0,0,0,0.4)] backdrop-blur-md">
        <button
          type="button"
          onClick={onBack}
          className="absolute left-2 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full text-slate-300 transition hover:bg-white/[0.06] focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/70"
          aria-label="Back to dashboard"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2.25}
            stroke="currentColor"
            className="h-6 w-6"
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>
        <h1
          id="alerts-center-title"
          className="text-[1.05rem] font-semibold tracking-tight text-slate-50"
        >
          Alerts Center
        </h1>
      </header>

      <div
        className="flex shrink-0 gap-0 border-b border-white/[0.06] bg-slate-950/60 px-3 backdrop-blur-sm"
        role="tablist"
        aria-label="Alert filters"
      >
        {TABS.map((tab) => {
          const active = filter === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setFilter(tab.id)}
              className={`flex-1 border-b-2 py-4 text-center text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-violet-500/60 ${
                active
                  ? 'border-violet-400 text-violet-200'
                  : 'border-transparent text-slate-500 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <main className="min-h-0 flex-1 overflow-y-auto px-5 py-10 md:px-8">
        <div className="mx-auto max-w-lg rounded-2xl border border-white/[0.07] bg-slate-950/50 p-10 text-center shadow-[0_24px_48px_-12px_rgba(0,0,0,0.55)] ring-1 ring-white/[0.04] backdrop-blur-md">
          <p className="text-sm text-slate-400">
            {filter === 'all' && 'Kick and loss events will appear here as they are detected.'}
            {filter === 'kicks' && 'No kick alerts in this view yet.'}
            {filter === 'losses' && 'No loss alerts in this view yet.'}
          </p>
          <p className="mt-3 text-xs text-slate-600">
            Monitoring stream continues in the background.
          </p>
        </div>
      </main>
    </div>
  )
}

export default AlertsCenter
