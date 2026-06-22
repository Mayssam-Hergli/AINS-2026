import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import LangToggle from '../components/LangToggle'
import Spinner from '../components/Spinner'

const SORA = { fontFamily: "'Sora', sans-serif" }

export default function LoginPage() {
  const { login } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const L = t.login

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || L.error_default)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      dir={lang === 'ar' ? 'rtl' : 'ltr'}
      className="min-h-screen flex flex-col"
      style={{ background: 'linear-gradient(180deg, #081F5C 0%, #050F2E 100%)' }}
    >
      {/* top bar */}
      <div className="flex items-center justify-between px-6 sm:px-10 pt-5">
        <Link to="/" className="font-black text-white/50 text-sm tracking-[0.25em] uppercase hover:text-white/80 transition-colors" style={SORA}>
          Massar
        </Link>
        <LangToggle dark />
      </div>

      {/* card */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* heading above card */}
          <div className="text-center mb-8">
            <h1
              className="font-black text-white"
              style={{ ...SORA, fontSize: 'clamp(2.2rem, 8vw, 3.2rem)', letterSpacing: 0 }}
            >
              Massar
            </h1>
            <p className="text-white/40 text-sm mt-2 font-light">{L.subtitle}</p>
          </div>

          <div
            className="bg-white rounded-2xl shadow-2xl p-8"
            style={{ boxShadow: '0 0 0 1px rgba(61,163,93,0.12), 0 32px 64px rgba(5,15,46,0.5)' }}
          >
            {/* green top accent bar */}
            <div
              className="w-12 h-0.5 rounded-full mb-6"
              style={{ background: 'linear-gradient(90deg, #3DA35D, #2d8a4e)', boxShadow: '0 0 12px rgba(61,163,93,0.5)' }}
            />

            <h2 className="text-xl font-semibold text-gray-800 mb-6" style={SORA}>{L.title}</h2>

            <form onSubmit={submit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{L.email}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-shadow"
                  style={{ '--tw-ring-color': '#3DA35D' }}
                  placeholder={L.email_ph}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{L.password}</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:border-transparent transition-shadow"
                  placeholder={L.password_ph}
                />
              </div>

              {error && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 hover:brightness-110 active:scale-[0.99]"
                style={{ background: '#3346AC', marginTop: '1.25rem' }}
              >
                {loading && <Spinner size="sm" />}
                {loading ? L.loading : L.submit}
              </button>
            </form>

            <p className="mt-6 text-center text-sm text-gray-400">
              {L.no_account}{' '}
              <Link to="/register" className="font-semibold hover:underline" style={{ color: '#3DA35D' }}>
                {L.register_link}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
