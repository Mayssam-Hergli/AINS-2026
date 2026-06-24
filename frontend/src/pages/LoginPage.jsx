import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { profilesApi } from '../api/profiles'
import Spinner from '../components/Spinner'

const SORA  = { fontFamily: "'Sora', sans-serif" }
const INTER = { fontFamily: "'Inter', sans-serif" }

export default function LoginPage() {
  const { login }              = useAuth()
  const { t, lang, toggleLang } = useLang()
  const navigate               = useNavigate()
  const isAr                   = lang === 'ar'
  const L                      = t.login

  const [email,      setEmail]      = useState('')
  const [password,   setPassword]   = useState('')
  const [error,      setError]      = useState(null)
  const [loading,    setLoading]    = useState(false)
  const [emailFocus, setEmailFocus] = useState(false)
  const [passFocus,  setPassFocus]  = useState(false)
  const [btnHover,   setBtnHover]   = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      // Route by diagnostic status: not done -> answer the questionnaire first,
      // already done -> straight to the dashboard scores.
      let dest = '/diagnostic'
      try {
        const token = localStorage.getItem('token')
        const list = await profilesApi.list(token)
        const status = list && list[0] ? list[0].status : undefined
        if (status === 'diagnostic_complete' || status === 'scored') dest = '/dashboard'
      } catch { /* default to /diagnostic */ }
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err.message || L.error_default)
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = (focused) => ({
    ...INTER,
    width: '100%',
    border: 'none',
    outline: 'none',
    borderRadius: '10px',
    padding: '11px 14px',
    fontSize: '0.9rem',
    color: '#081F5C',
    backgroundColor: '#FAFBFF',
    boxShadow: focused
      ? '0 0 0 2px #3346AC, 0 0 16px rgba(61,163,93,0.12)'
      : '0 0 0 1.5px rgba(112,150,209,0.25)',
    transition: 'box-shadow 0.2s ease',
  })

  return (
    <div
      dir={isAr ? 'rtl' : 'ltr'}
      className="min-h-screen flex flex-col"
      style={{ backgroundColor: '#FFFFFF' }}
    >
      {/* Top bar */}
      <div
        className="flex items-center justify-between px-6 sm:px-12 py-5"
        style={{ borderBottom: '1px solid rgba(112,150,209,0.1)' }}
      >
        <Link
          to="/"
          className="text-2xl font-black tracking-tight transition-opacity hover:opacity-70"
          style={{ ...SORA, color: '#081F5C' }}
        >
          {isAr ? 'مسار' : 'Massar'}
        </Link>

        {/* FR / AR toggle */}
        <div
          className="flex items-center p-1 rounded-full"
          style={{ backgroundColor: '#F5F7FF', border: '1px solid rgba(112,150,209,0.18)' }}
        >
          <button
            onClick={() => isAr && toggleLang()}
            className="px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200"
            style={!isAr
              ? { backgroundColor: '#3346AC', color: '#fff' }
              : { color: '#7096D1' }}
          >
            FR
          </button>
          <button
            onClick={() => !isAr && toggleLang()}
            className="px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200"
            style={isAr
              ? { backgroundColor: '#3346AC', color: '#fff' }
              : { color: '#7096D1' }}
          >
            AR
          </button>
        </div>
      </div>

      {/* Centered card */}
      <div className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">

          {/* Above-card heading */}
          <div className="text-center mb-10 flex flex-col items-center">
            <img
              src={isAr ? '/massar-logo-ar.svg' : '/massar-logo-fr.svg'}
              alt="Massar"
              className="mb-1"
              style={{ height: 'clamp(8.6rem, 26.5vw, 12.5rem)', width: 'auto', maxWidth: '96%' }}
            />
            <p className="text-sm" style={{ ...INTER, color: '#7096D1' }}>
              {L.subtitle}
            </p>
          </div>

          {/* Card */}
          <div
            className="bg-white rounded-2xl p-8"
            style={{
              boxShadow: '0 8px 40px rgba(51,70,172,0.08), 0 1px 4px rgba(51,70,172,0.05)',
              border: '1px solid rgba(112,150,209,0.12)',
              borderTop: '3px solid #3DA35D',
            }}
          >
            <h2 className="text-lg font-bold mb-7" style={{ ...SORA, color: '#081F5C' }}>
              {L.title}
            </h2>

            <form onSubmit={submit} className="flex flex-col gap-5">

              <div>
                <label
                  className="block text-xs font-semibold mb-2"
                  style={{ ...INTER, color: '#7096D1', letterSpacing: '0.03em' }}
                >
                  {L.email}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setEmailFocus(true)}
                  onBlur={() => setEmailFocus(false)}
                  required
                  placeholder={L.email_ph}
                  style={inputStyle(emailFocus)}
                />
              </div>

              <div>
                <label
                  className="block text-xs font-semibold mb-2"
                  style={{ ...INTER, color: '#7096D1', letterSpacing: '0.03em' }}
                >
                  {L.password}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setPassFocus(true)}
                  onBlur={() => setPassFocus(false)}
                  required
                  placeholder={L.password_ph}
                  style={inputStyle(passFocus)}
                />
              </div>

              {error && (
                <div
                  className="text-sm px-4 py-2.5 rounded-xl"
                  style={{
                    ...INTER,
                    color: '#c0392b',
                    backgroundColor: '#FFF5F5',
                    border: '1px solid rgba(192,57,43,0.15)',
                  }}
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                onMouseEnter={() => setBtnHover(true)}
                onMouseLeave={() => setBtnHover(false)}
                className="w-full flex items-center justify-center gap-2.5 py-3 rounded-xl font-semibold text-white disabled:opacity-60 active:scale-[0.99] mt-1"
                style={{
                  ...INTER,
                  fontSize: '0.95rem',
                  backgroundColor: btnHover ? '#3DA35D' : '#3346AC',
                  boxShadow: btnHover
                    ? '0 8px 24px rgba(61,163,93,0.25)'
                    : '0 4px 16px rgba(51,70,172,0.18)',
                  transition: 'background-color 0.25s ease, box-shadow 0.25s ease',
                }}
              >
                {loading && <Spinner size="sm" />}
                {loading ? L.loading : L.submit}
              </button>
            </form>

            <p
              className="mt-7 text-center text-xs"
              style={{ ...INTER, color: '#7096D1' }}
            >
              {L.no_account}{' '}
              <Link
                to="/register"
                className="font-semibold transition-colors hover:underline"
                style={{ color: '#3DA35D' }}
              >
                {L.register_link}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
