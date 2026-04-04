import AppLayout from './components/AppLayout'

function App() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-gradient-to-br from-slate-950 via-[#12102a] to-violet-950 text-slate-100 antialiased">
      <div
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,rgba(109,40,217,0.22),transparent_55%)]"
        aria-hidden
      />
      <div className="relative z-0">
        <AppLayout />
      </div>
    </div>
  )
}

export default App
