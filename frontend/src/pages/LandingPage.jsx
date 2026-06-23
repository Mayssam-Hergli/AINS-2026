import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { ArrowRight, Leaf, BarChart3, Share2, Sparkles } from 'lucide-react'

const SORA  = { fontFamily: "'Sora', sans-serif" }
const INTER = { fontFamily: "'Inter', sans-serif" }

const WORDS_FR = [
  { text: 'innover', x: '5%',  y: '16%', sz: '1.55rem', anim: 'float-a', dur: 8,  del: 0,    tint: 'blue'  },
  { text: 'créer',   x: '78%', y: '12%', sz: '1.85rem', anim: 'float-b', dur: 9,  del: 1200, tint: 'green' },
  { text: 'lancer',  x: '8%',  y: '50%', sz: '1.35rem', anim: 'float-c', dur: 10, del: 2000, tint: 'green' },
  { text: 'grandir', x: '84%', y: '36%', sz: '1.65rem', anim: 'float-a', dur: 8.5,del: 500,  tint: 'blue'  },
  { text: 'impact',  x: '50%', y: '78%', sz: '1.3rem',  anim: 'float-b', dur: 9.5,del: 2800, tint: 'green' },
  { text: 'vision',  x: '14%', y: '4%',  sz: '1.25rem', anim: 'float-c', dur: 11, del: 1700, tint: 'blue'  },
  { text: 'bâtir',   x: '18%', y: '82%', sz: '1.4rem',  anim: 'float-a', dur: 9,  del: 3400, tint: 'blue'  },
]
const WORDS_AR = [
  { text: 'ابتكر', x: '5%',  y: '16%', sz: '1.55rem', anim: 'float-a', dur: 8,  del: 0,    tint: 'blue'  },
  { text: 'أنشئ',  x: '78%', y: '12%', sz: '1.85rem', anim: 'float-b', dur: 9,  del: 1200, tint: 'green' },
  { text: 'انطلق', x: '8%',  y: '50%', sz: '1.35rem', anim: 'float-c', dur: 10, del: 2000, tint: 'green' },
  { text: 'نمِّ',  x: '84%', y: '36%', sz: '1.65rem', anim: 'float-a', dur: 8.5,del: 500,  tint: 'blue'  },
  { text: 'تأثير', x: '50%', y: '78%', sz: '1.3rem',  anim: 'float-b', dur: 9.5,del: 2800, tint: 'green' },
  { text: 'رؤية',  x: '14%', y: '4%',  sz: '1.25rem', anim: 'float-c', dur: 11, del: 1700, tint: 'blue'  },
  { text: 'بناء',  x: '18%', y: '82%', sz: '1.4rem',  anim: 'float-a', dur: 9,  del: 3400, tint: 'blue'  },
]

const PARTNERS = ['I', 'II', 'III', 'IV', 'V', 'VI']

export default function LandingPage() {
  const { t, lang, toggleLang } = useLang()
  const isAr     = lang === 'ar'
  const [ready, setReady] = useState(false)
  const wordRefs = useRef([])

  useEffect(() => {
    const id = setTimeout(() => setReady(true), 80)
    return () => clearTimeout(id)
  }, [])

  useEffect(() => {
    let rafId
    const onMove = (e) => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        const mx = (e.clientX / window.innerWidth  - 0.5) * 2
        const my = (e.clientY / window.innerHeight - 0.5) * 2
        wordRefs.current.forEach((el, i) => {
          if (!el) return
          const d = 0.14 + (i % 4) * 0.09
          el.style.transform = `translate(${mx * d * 13}px, ${my * d * 8}px)`
        })
      })
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => { window.removeEventListener('mousemove', onMove); cancelAnimationFrame(rafId) }
  }, [])

  const WORDS = isAr ? WORDS_AR : WORDS_FR

  const fadeUp = (delay = 0) => ({
    opacity:   ready ? 1 : 0,
    transform: ready ? 'translateY(0)' : 'translateY(22px)',
    transition: `opacity 0.75s ease ${delay}ms, transform 0.75s ease ${delay}ms`,
  })

  return (
    <div
      dir={isAr ? 'rtl' : 'ltr'}
      className="relative min-h-screen overflow-x-hidden"
      style={{ backgroundColor: '#FFFFFF', color: '#081F5C' }}
    >

      {/* Floating background words */}
      {WORDS.map((w, i) => (
        <div
          key={i}
          ref={(el) => { wordRefs.current[i] = el }}
          className="absolute pointer-events-none select-none z-0"
          style={{
            left: w.x,
            top: w.y,
            transition: 'transform 1.6s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          }}
        >
          <span
            className="block font-semibold"
            style={{
              ...SORA,
              fontSize: w.sz,
              color: w.tint === 'green' ? '#3DA35D' : '#7096D1',
              opacity: 0.13,
              animation: `${w.anim} ${w.dur}s ease-in-out ${w.del}ms infinite`,
            }}
          >
            {w.text}
          </span>
        </div>
      ))}

      {/* Navigation */}
      <header
        className="fixed top-0 left-0 right-0 z-50"
        style={{
          backgroundColor: 'rgba(255,255,255,0.92)',
          backdropFilter: 'blur(18px)',
          WebkitBackdropFilter: 'blur(18px)',
          borderBottom: '1px solid rgba(112,150,209,0.1)',
        }}
      >
        <div className="max-w-container mx-auto px-6 md:px-12 py-4 flex items-center justify-between">

          <span className="text-3xl font-black tracking-tight" style={{ ...SORA, color: '#081F5C' }}>
            {isAr ? 'مسار' : 'Massar'}
          </span>

          <div className="flex items-center gap-3">
            {/* FR / AR toggle */}
            <div
              className="flex items-center p-1 rounded-full"
              style={{ backgroundColor: '#F5F7FF', border: '1px solid rgba(112,150,209,0.18)' }}
            >
              <button
                onClick={() => isAr && toggleLang()}
                className="w-11 py-1 rounded-full text-xs font-semibold transition-all duration-200 text-center"
                style={!isAr
                  ? { backgroundColor: '#3346AC', color: '#fff' }
                  : { color: '#7096D1' }}
              >
                FR
              </button>
              <button
                onClick={() => !isAr && toggleLang()}
                className="w-11 py-1 rounded-full text-xs font-semibold transition-all duration-200 text-center"
                style={isAr
                  ? { backgroundColor: '#3346AC', color: '#fff' }
                  : { color: '#7096D1' }}
              >
                AR
              </button>
            </div>

            <Link
              to="/login"
              className="hidden sm:inline-flex px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 hover:bg-blue-50 active:scale-95"
              style={{ ...INTER, border: '1.5px solid #3346AC', color: '#3346AC' }}
            >
              {t.landing.cta_login}
            </Link>

            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold text-white transition-all duration-200 hover:brightness-110 active:scale-95"
              style={{ ...INTER, backgroundColor: '#3346AC' }}
            >
              {isAr ? 'ابدأ' : 'Commencer'}
              <ArrowRight size={14} style={isAr ? { transform: 'scaleX(-1)' } : {}} />
            </Link>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="relative z-10">

        {/* Hero */}
        <section className="max-w-5xl mx-auto px-6 flex flex-col items-center justify-center text-center gap-5 min-h-screen">

          {/* Wordmark + trajectory line, sitting directly under it, no gap */}
          <div style={fadeUp(0)} className="relative inline-block mb-9">
            <h1
              className="font-bold leading-none"
              style={{
                ...SORA,
                fontWeight: 700,
                fontSize: 'clamp(5.5rem, 15vw, 10rem)',
                color: '#081F5C',
                letterSpacing: '-0.02em',
              }}
            >
              {isAr ? 'مسار' : 'Massar'}
            </h1>

            {/* Trajectory line, anchored to the bottom of the wordmark box */}
            <svg
              viewBox="0 0 520 28"
              fill="none"
              className="absolute left-0 w-full overflow-visible pointer-events-none"
              style={{ bottom: '-30px', height: '28px', ...(isAr ? { transform: 'scaleX(-1)' } : {}) }}
            >
              <path
                className="path-line"
                d="M6 20 Q 180 4 260 13 T 514 17"
                stroke="#3346AC"
                strokeWidth="1.4"
                strokeLinecap="round"
                opacity="0.45"
              />
              <circle cx="514" cy="17" r="5" fill="#3DA35D" />
            </svg>
          </div>

          {/* Tagline */}
          <p
            className="max-w-xl"
            style={{
              ...SORA,
              fontSize: 'clamp(1.05rem, 2.4vw, 1.4rem)',
              fontWeight: 500,
              lineHeight: 1.48,
              color: '#7096D1',
              ...fadeUp(260),
            }}
          >
            {isAr ? (
              <>
                اعرف{' '}
                <span style={{ color: '#081F5C', fontWeight: 700 }}>مسارك</span>.{' '}
                اختر{' '}
                <span style={{ color: '#3DA35D', fontWeight: 700 }}>طريقك</span>.
              </>
            ) : (
              <>
                Connaître votre{' '}
                <span style={{ color: '#081F5C', fontWeight: 700 }}>trajectoire</span>.{' '}
                Choisir votre{' '}
                <span style={{ color: '#3DA35D', fontWeight: 700 }}>chemin</span>.
              </>
            )}
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-4 my-8 mt-2" style={fadeUp(380)}>
            <Link
              to="/register"
              className="group btn-cta-primary flex items-center justify-center gap-2.5 px-9 py-3.5 rounded-xl font-semibold hover:shadow-[0_8px_26px_rgba(61,163,93,0.35)]"
              style={{ ...INTER, fontSize: '1rem' }}
            >
              {isAr ? 'ابدأ التشخيص' : 'Commencer le diagnostic'}
              <ArrowRight
                size={18}
                className="group-hover:translate-x-1 transition-transform duration-200"
                style={isAr ? { transform: 'scaleX(-1)' } : {}}
              />
            </Link>
            <Link
              to="/login"
              className="btn-cta-secondary flex items-center justify-center px-9 py-3.5 rounded-xl font-semibold"
              style={{ ...INTER, fontSize: '1rem' }}
            >
              {t.landing.cta_login}
            </Link>
          </div>
        </section>

        {/* Feature cards */}
        <section className="py-32 px-6" style={{ backgroundColor: '#FFF9F0' }}>
          <div className="max-w-6xl mx-auto">
            <h2
              className="text-center font-bold mb-16"
              style={{
                ...SORA,
                fontSize: 'clamp(1.5rem, 3.2vw, 2.1rem)',
                color: '#081F5C',
                lineHeight: 1.25,
              }}
            >
              {isAr
                ? 'أدوات مصممة لرائد الأعمال التونسي'
                : "Conçu pour l'entrepreneur tunisien"}
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: <BarChart3 size={20} />,
                  title: isAr ? 'تشخيص النمو' : 'Diagnostic de Croissance',
                  desc: isAr
                    ? 'تقييم شامل لأداء مشروعك باستخدام خوارزميات الذكاء الاصطناعي لتحديد نقاط القوة وفرص التحسين.'
                    : "Une évaluation complète de la performance de votre entreprise grâce à des algorithmes d'IA pour identifier vos points forts et axes d'amélioration.",
                },
                {
                  icon: <Share2 size={20} />,
                  title: isAr ? 'خريطة المنظومة' : "Cartographie de l'Écosystème",
                  desc: isAr
                    ? 'خريطة تفاعلية تربطك بالمستثمرين والحاضنات والشركاء الاستراتيجيين في تونس وخارجها.'
                    : 'Une carte interactive vous connectant aux investisseurs, incubateurs et partenaires stratégiques en Tunisie et au-delà.',
                },
                {
                  icon: <Sparkles size={20} />,
                  title: isAr ? 'توصيات مخصصة' : 'Recommandations Personnalisées',
                  desc: isAr
                    ? 'مسارات نمو مخصصة بناءً على مرحلة نضج مشروعك وقطاع نشاطك.'
                    : 'Des parcours de croissance sur mesure basés sur le stade de maturité de votre entreprise et votre secteur.',
                },
                {
                  icon: <Leaf size={20} />,
                  title: isAr ? 'مؤشر الأثر البيئي' : "Score d'Impact Environnemental",
                  desc: isAr
                    ? 'مؤشر يعتمد على منهجية برنامج الأمم المتحدة الإنمائي لقياس وتعزيز الأثر البيئي الإيجابي لمشروعك.'
                    : "Un score basé sur la méthodologie du PNUD pour mesurer et valoriser l'impact environnemental positif de votre entreprise.",
                },
              ].map(({ icon, title, desc }, i) => (
                <div
                  key={i}
                  className="relative bg-white rounded-2xl p-6 flex flex-col gap-3 transition-all duration-300 hover:-translate-y-1 cursor-pointer"
                  style={{
                    boxShadow: '0 2px 20px rgba(51,70,172,0.06)',
                    border: '1px solid rgba(112,150,209,0.12)',
                    textAlign: isAr ? 'right' : 'left',
                  }}
                >
                  <div
                    className="relative w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: '#EEF1FF', color: '#3346AC' }}
                  >
                    {icon}
                    <span
                      className="absolute rounded-full"
                      style={{
                        width: '8px',
                        height: '8px',
                        top: '-3px',
                        ...(isAr ? { left: '-3px' } : { right: '-3px' }),
                        backgroundColor: '#3DA35D',
                      }}
                    />
                  </div>
                  <h3 className="font-bold text-base" style={{ ...SORA, color: '#081F5C' }}>
                    {title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ ...INTER, color: '#7096D1' }}>
                    {desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer
        className="py-20 px-6"
        style={{ backgroundColor: '#FFFFFF', borderTop: '1px solid rgba(112,150,209,0.1)' }}
      >
        <div className="max-w-5xl mx-auto flex flex-col items-center gap-12">

          <div className="text-center">
            <p
              className="text-xs font-semibold uppercase mb-3"
              style={{ ...INTER, color: '#7096D1', letterSpacing: '0.13em' }}
            >
              {isAr ? 'بدعم من رواد المنظومة' : "Propulsé par des leaders de l'écosystème"}
            </p>
            <div className="w-8 h-0.5 mx-auto rounded-full" style={{ backgroundColor: '#3DA35D' }} />
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-6 gap-4 w-full">
            {PARTNERS.map((n) => (
              <div
                key={n}
                className="h-14 rounded-xl flex items-center justify-center transition-all duration-300 hover:opacity-100"
                style={{
                  backgroundColor: '#F8F9FE',
                  border: '1px solid rgba(112,150,209,0.13)',
                  opacity: 0.5,
                }}
              >
                <span className="text-xs font-semibold" style={{ ...INTER, color: '#7096D1' }}>
                  Partner {n}
                </span>
              </div>
            ))}
          </div>

          <div
            className="w-full pt-10 flex flex-col md:flex-row justify-between items-center gap-6"
            style={{ borderTop: '1px solid rgba(112,150,209,0.08)' }}
          >
            <span className="text-xl font-black tracking-tight" style={{ ...SORA, color: '#081F5C' }}>
              {isAr ? 'مسار' : 'Massar'}
            </span>
            <nav className="flex flex-wrap justify-center gap-6">
              {(isAr
                ? ['التأثير البيئي', 'ملاحظات قانونية', 'الخصوصية', 'الشروط العامة']
                : ['Impact Environnemental', 'Mentions Légales', 'Confidentialité', 'Conditions Générales']
              ).map((label) => (
                <a
                  key={label}
                  href="#"
                  className="text-xs transition-colors hover:text-blue-600"
                  style={{ ...INTER, color: '#7096D1' }}
                >
                  {label}
                </a>
              ))}
            </nav>
            <p className="text-xs" style={{ ...INTER, color: 'rgba(112,150,209,0.55)' }}>
              © 2024 Massar.{' '}
              {isAr ? 'جميع الحقوق محفوظة.' : 'Tous droits réservés.'}
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
