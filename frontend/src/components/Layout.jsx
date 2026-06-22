import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import LangToggle from './LangToggle'
import SponsorRoller from './SponsorRoller'

const SORA = { fontFamily: "'Sora', sans-serif" }

export default function Layout() {
  const { user, logout } = useAuth()
  const { t } = useLang()
  const navigate = useNavigate()
  const location = useLocation()

  const NAV = [
    { to: '/dashboard', label: t.nav.dashboard },
    { to: '/assistant',  label: t.nav.assistant },
  ]

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header style={{ background: '#081F5C' }} className="text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Link
            to="/dashboard"
            className="text-xl font-black tracking-tight text-white hover:text-white/80 transition-colors"
            style={SORA}
          >
            Massar
          </Link>

          <nav className="flex items-center gap-5">
            {NAV.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={`text-sm font-medium transition-colors ${
                  location.pathname === to
                    ? 'text-white'
                    : 'text-white/50 hover:text-white'
                }`}
              >
                {label}
              </Link>
            ))}

            <div className="flex items-center gap-3 ml-3 pl-3 border-l border-white/15">
              <span className="text-xs text-white/40 hidden sm:block">{user?.email}</span>
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-white/50 hover:text-white transition-colors"
              >
                {t.nav.logout}
              </button>
              <LangToggle dark />
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      <footer style={{ background: '#081F5C' }} className="border-t border-white/[0.07]">
        <SponsorRoller variant="dark" />
      </footer>
    </div>
  )
}
