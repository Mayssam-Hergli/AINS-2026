import { useLang } from '../context/LanguageContext'

const LOGOS = ['Logo 1', 'Logo 2', 'Logo 3', 'Logo 4', 'Logo 5', 'Logo 6']

export default function SponsorRoller({ variant = 'dark' }) {
  const { t } = useLang()
  const isDark = variant === 'dark'
  const track = [...LOGOS, ...LOGOS] // duplicate for seamless loop

  return (
    <div className={`py-5 overflow-hidden ${isDark ? '' : 'bg-gray-50 border-t border-gray-100'}`}>
      <p
        className={`text-center text-[10px] tracking-[0.2em] uppercase mb-4 font-medium ${
          isDark ? 'text-white/20' : 'text-gray-400'
        }`}
      >
        {t.nav?.partners ?? t.landing?.partners}
      </p>
      <div className="overflow-hidden px-4">
        <div className="sponsor-track flex gap-5" style={{ width: 'max-content' }}>
          {track.map((label, i) => (
            <div
              key={i}
              className={`flex items-center justify-center h-11 w-32 rounded-xl flex-shrink-0 text-xs font-medium tracking-wide ${
                isDark
                  ? 'bg-white/[0.05] border border-white/[0.09] text-white/35'
                  : 'bg-white border border-gray-200 text-gray-400 shadow-sm'
              }`}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
