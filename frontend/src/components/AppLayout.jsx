import { useState } from 'react'
import Dashboard from './Dashboard'

const TABS = [
  {
    id: 'home',
    label: 'Home',
    navLabel: 'Home',
  },
  {
    id: 'reports',
    label: 'Reports',
    navLabel: 'Reports',
  },
  {
    id: 'profile',
    label: 'Profile',
    navLabel: 'Profile',
  },
]

/** Monitoring dashboard: panel + live chart bars */
function IconNavHome({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      className={className}
      aria-hidden
    >
      <path
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M7.5 14.25v2.25m3-4.872v-6.75m0 0l-2.25 2.25m2.25-2.25l2.25 2.25M3 18.75h-.75a2.25 2.25 0 01-2.25-2.25V6a2.25 2.25 0 012.25-2.25h16.5A2.25 2.25 0 0121 6v10.5a2.25 2.25 0 01-2.25 2.25H3.75a2.25 2.25 0 01-2.25-2.25V6z"
      />
    </svg>
  )
}

/** Report: document with fold + ruled lines (Heroicons-style) */
function IconNavReports({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      className={className}
      aria-hidden
    >
      <path
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
      />
      <path
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth={1.5}
        d="M9 12.75h6M9 15.75h4.5M9 18.75h6"
      />
    </svg>
  )
}

/** Profile: classic user silhouette */
function IconNavProfile({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      className={className}
      aria-hidden
    >
      <path
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
      />
      <path
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
      />
    </svg>
  )
}

const TAB_ICONS = {
  home: IconNavHome,
  reports: IconNavReports,
  profile: IconNavProfile,
}

function ReportsPage() {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col px-5 pb-8 pt-[max(1.5rem,env(safe-area-inset-top))] md:max-w-2xl md:px-8 md:pb-12">
      <h1 className="mb-10 text-center text-2xl font-semibold tracking-tight text-slate-50 md:mb-12">
        Reports
      </h1>
      <div className="rounded-2xl border border-white/[0.07] bg-slate-950/45 p-10 text-center shadow-[0_24px_48px_-12px_rgba(0,0,0,0.55)] ring-1 ring-white/[0.04] backdrop-blur-md">
        <IconNavReports className="mx-auto h-12 w-12 text-cyan-400/90" />
        <p className="mt-5 text-base font-medium text-slate-200">Reports</p>
        <p className="mt-2 text-sm text-slate-500">
          Summaries and exports will be available here.
        </p>
      </div>
    </div>
  )
}

function ProfilePage() {
  return (
    <div className="mx-auto flex w-full max-w-lg flex-col px-5 pb-8 pt-[max(1.5rem,env(safe-area-inset-top))] md:max-w-2xl md:px-8 md:pb-12">
      <h1 className="mb-10 text-center text-2xl font-semibold tracking-tight text-slate-50 md:mb-12">
        Profile
      </h1>
      <div className="rounded-2xl border border-white/[0.07] bg-slate-950/45 p-10 text-center shadow-[0_24px_48px_-12px_rgba(0,0,0,0.55)] ring-1 ring-white/[0.04] backdrop-blur-md">
        <IconNavProfile className="mx-auto h-12 w-12 text-cyan-400/90" />
        <p className="mt-5 text-base font-medium text-slate-200">Account</p>
        <p className="mt-2 text-sm text-slate-500">
          Settings and user preferences will appear here.
        </p>
      </div>
    </div>
  )
}

function AppLayout() {
  const [activeTab, setActiveTab] = useState('home')

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside
        className="relative z-30 hidden w-[15.5rem] shrink-0 flex-col border-r border-zinc-800/90 bg-[#0a0a0a] py-10 pl-6 pr-5 md:flex"
        aria-label="Main navigation"
      >
        <p className="mb-10 px-1 font-sans text-[10px] font-semibold tracking-[0.42em] text-zinc-500">
          NAVIGATE
        </p>
        <nav className="flex flex-col gap-1.5">
          {TABS.map((tab) => {
            const Icon = TAB_ICONS[tab.id]
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                aria-current={active ? 'page' : undefined}
                className={`group relative flex w-full items-center gap-3.5 rounded-xl px-3.5 py-3.5 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a0a] ${
                  active
                    ? 'border border-cyan-400/95 bg-cyan-500/[0.06] text-cyan-50 shadow-[0_0_0_1px_rgba(34,211,238,0.55),0_0_28px_rgba(34,211,238,0.28),inset_0_1px_0_rgba(255,255,255,0.06)]'
                    : 'border border-transparent text-zinc-500 hover:bg-zinc-900/80 hover:text-zinc-300'
                }`}
              >
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition ${
                    active
                      ? 'text-cyan-300'
                      : 'text-zinc-600 group-hover:text-zinc-400'
                  }`}
                >
                  <Icon className="h-[22px] w-[22px]" />
                </span>
                <span
                  className={`truncate font-sans text-[0.9375rem] tracking-tight ${
                    active ? 'font-semibold text-white' : 'font-medium'
                  }`}
                >
                  {tab.navLabel}
                </span>
              </button>
            )
          })}
        </nav>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <main
          id="main-content"
          className="flex-1 overflow-y-auto pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:px-2 md:pb-10"
        >
          {activeTab === 'home' && <Dashboard />}
          {activeTab === 'reports' && <ReportsPage />}
          {activeTab === 'profile' && <ProfilePage />}
        </main>

        <nav
          className="fixed bottom-0 left-0 right-0 z-40 border-t border-zinc-800/90 bg-[#0a0a0a]/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-12px_40px_rgba(0,0,0,0.5)] backdrop-blur-md md:hidden"
          aria-label="Main navigation"
        >
          <div className="mx-auto flex min-h-[3.85rem] max-w-lg items-stretch justify-around px-2">
            {TABS.map((tab) => {
              const Icon = TAB_ICONS[tab.id]
              const active = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  aria-current={active ? 'page' : undefined}
                  className={`flex min-w-0 flex-1 flex-col items-center justify-center gap-1 rounded-t-xl px-2 py-2.5 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-400/60 ${
                    active ? 'text-cyan-200' : 'text-zinc-500 hover:text-zinc-400'
                  }`}
                >
                  <span
                    className={`flex h-10 w-10 items-center justify-center rounded-xl border transition ${
                      active
                        ? 'border-cyan-400/90 bg-cyan-500/10 text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.35)]'
                        : 'border-transparent bg-transparent'
                    }`}
                  >
                    <Icon className="h-[22px] w-[22px]" />
                  </span>
                  <span className="max-w-full truncate font-sans text-[0.65rem] font-semibold tracking-tight">
                    {tab.navLabel}
                  </span>
                </button>
              )
            })}
          </div>
        </nav>
      </div>
    </div>
  )
}

export default AppLayout
