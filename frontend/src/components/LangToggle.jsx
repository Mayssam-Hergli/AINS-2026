import { useLang } from '../context/LanguageContext'

export default function LangToggle({ dark = true }) {
  const { lang, toggleLang } = useLang()

  const base = dark
    ? 'border-white/25 text-white/70 hover:border-white/55 hover:text-white'
    : 'border-gray-300 text-gray-600 hover:border-gray-500 hover:text-gray-900'

  return (
    <button
      onClick={toggleLang}
      aria-label="Toggle language"
      className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold tracking-widest transition-colors duration-200 ${base}`}
      style={{ width: '76px', flexShrink: 0 }}
    >
      <span style={{ opacity: lang === 'fr' ? 1 : 0.35 }}>FR</span>
      <span style={{ opacity: 0.28 }}>|</span>
      <span style={{ opacity: lang === 'ar' ? 1 : 0.35, fontFamily: 'system-ui' }}>AR</span>
    </button>
  )
}
