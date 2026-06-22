import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { ArrowRight, BarChart3, Network, Sparkles } from 'lucide-react'

const SORA  = { fontFamily: "'Sora', sans-serif" }
const INTER = { fontFamily: "'Inter', sans-serif" }
const KUFI  = { fontFamily: "'Noto Kufi Arabic', sans-serif" }

const WORDS_FR = [
  { text: 'innover', l: '6%',  t: '14%', sz: '1.1rem', anim: 'float-a', dur: 14, del: 0    },
  { text: 'créer',   l: '78%', t: '11%', sz: '1.4rem', anim: 'float-b', dur: 16, del: 2000 },
  { text: 'lancer',  l: '12%', t: '46%', sz: '0.9rem', anim: 'float-c', dur: 18, del: 3500 },
  { text: 'grandir', l: '84%', t: '33%', sz: '1.2rem', anim: 'float-a', dur: 15, del: 500  },
  { text: 'impact',  l: '50%', t: '72%', sz: '0.85rem',anim: 'float-b', dur: 17, del: 4500 },
  { text: 'vision',  l: '42%', t: '9%',  sz: '0.8rem', anim: 'float-c', dur: 20, del: 3000 },
]
const WORDS_AR = [
  { text: 'ابتكر', l: '6%',  t: '14%', sz: '1.1rem', anim: 'float-a', dur: 14, del: 0    },
  { text: 'أنشئ',  l: '78%', t: '11%', sz: '1.4rem', anim: 'float-b', dur: 16, del: 2000 },
  { text: 'انطلق', l: '12%', t: '46%', sz: '0.9rem', anim: 'float-c', dur: 18, del: 3500 },
  { text: 'نمِّ',  l: '84%', t: '33%', sz: '1.2rem', anim: 'float-a', dur: 15, del: 500  },
  { text: 'تأثير', l: '50%', t: '72%', sz: '0.85rem',anim: 'float-b', dur: 17, del: 4500 },
  { text: 'رؤية',  l: '42%', t: '9%',  sz: '0.8rem', anim: 'float-c', dur: 20, del: 3000 },
]

const PARTNERS = ['I', 'II', 'III', 'IV', 'V', 'VI']

export default function LandingPage() {
  const { t, lang, toggleLang } = useLang()
  const isAr    = lang === 'ar'
  const [ready, setReady] = useState(false)
  const wordRefs = useRef([])

  useEffect(() => {
    const id = setTimeout(() => setReady(true), 80)
    return () => clearTimeout(id)
  }, [])

  useEffect(() => {
    const mouse = { x: 0, y: 0 }
    let rafId
    const onMove = (e) => {
      mouse.x = (e.clientX / window.innerWidth  - 0.5) * 2
      mouse.y = (e.clientY / window.innerHeight - 0.5) * 2
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(() => {
        wordRefs.current.forEach((el, i) => {
          if (!el) return
          const d = 0.18 + (i % 4) * 0.11
          el.style.transform = `translate(${mouse.x * d * 14}px, ${mouse.y * d * 9}px)`
        })
      })
    }
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => { window.removeEventListener('mousemove', onMove); cancelAnimationFrame(rafId) }
  }, [])

  const WORDS = isAr ? WORDS_AR : WORDS_FR
  const titleFont = isAr ? KUFI : SORA

  const fadeIn  = (delay = 0) => ({
    opacity:   ready ? 1 : 0,
    transform: ready ? 'translateY(0)' : 'translateY(18px)',
    transition: `opacity 0.7s ease ${delay}ms, transform 0.7s ease ${delay}ms`,
  })

  return (
    <div
      dir={isAr ? 'rtl' : 'ltr'}
      className="relative min-h-screen overflow-x-hidden"
      style={{ backgroundColor: '#f9f9ff', color: '#001b3b' }}
    >

      {/* ── Floating background words ── */}
      {WORDS.map((w, i) => (
        <div
          key={i}
          ref={(el) => { wordRefs.current[i] = el }}
          className="absolute pointer-events-none select-none z-0"
          style={{
            left: w.l,
            top: w.t,
            transition: 'transform 1.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          }}
        >
          <span
            className="block font-semibold"
            style={{
              ...SORA,
              fontSize: w.sz,
              opacity: 0.10,
              color: '#162c94',
              animation: `${w.anim} ${w.dur}s ease-in-out ${w.del}ms infinite`,
            }}
          >
            {w.text}
          </span>
        </div>
      ))}

      {/* ── Fixed Navigation ── */}
      <header
        className="fixed top-0 left-0 right-0 z-50"
        style={{
          backgroundColor: 'rgba(249,249,255,0.85)',
          backdropFilter: 'blur(14px)',
          WebkitBackdropFilter: 'blur(14px)',
          borderBottom: '1px solid rgba(197,197,213,0.2)',
        }}
      >
        <div className="max-w-container mx-auto px-6 md:px-16 py-4 flex items-center justify-between">

          {/* Logo */}
          <img
            src={isAr ? '/massar-logo-ar.svg' : '/massar-logo-fr.svg'}
            alt="Massar"
            style={{ width: '200px', height: '60px', objectFit: 'contain', objectPosition: 'center' }}
          />

          {/* Right controls */}
          <div className="flex items-center gap-3">

            {/* FR / AR pill toggle */}
            <div
              className="flex items-center p-1 rounded-full"
              style={{ backgroundColor: '#e7eeff', border: '1px solid rgba(197,197,213,0.35)' }}
            >
              <button
                onClick={() => isAr && toggleLang()}
                className="px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200"
                style={
                  !isAr
                    ? { backgroundColor: '#162c94', color: '#fff' }
                    : { color: '#454652' }
                }
              >
                FR
              </button>
              <button
                onClick={() => !isAr && toggleLang()}
                className="px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200"
                style={
                  isAr
                    ? { backgroundColor: '#162c94', color: '#fff' }
                    : { color: '#454652' }
                }
              >
                AR
              </button>
            </div>

            {/* Se connecter */}
            <Link
              to="/login"
              className="hidden sm:flex px-5 py-2 rounded-lg border font-medium transition-all hover:bg-surface-container-high active:scale-95"
              style={{ ...INTER, borderColor: '#162c94', color: '#162c94', fontSize: isAr ? '0.78rem' : '0.875rem' }}
            >
              {t.landing.cta_login}
            </Link>

            {/* Commencer */}
            <Link
              to="/register"
              className="px-5 py-2 rounded-lg text-white font-medium transition-all hover:opacity-90 active:scale-95"
              style={{ ...INTER, backgroundColor: '#3346AC', fontSize: isAr ? '0.78rem' : '0.875rem' }}
            >
              {isAr ? 'ابدأ' : 'Commencer'}
            </Link>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="relative z-10 pt-24">

        {/* Hero */}
        <section className="max-w-container mx-auto px-3 md:px-6 flex flex-col items-center text-center pt-0 pb-20">

          {/* Big wordmark */}
          <div style={fadeIn(0)}>
            <img
              src={isAr ? '/massar-logo-ar.svg' : '/massar-logo-fr.svg'}
              alt="Massar"
              style={{ width: 'min(900px, 92vw)', height: 'auto', display: 'block', margin: '0 auto', marginBottom: '-10rem' }}
            />

            {/* Decorative trajectory path */}
            <svg
              className="overflow-visible pointer-events-none"
              style={{ display: 'block', width: 'min(900px, 92vw)', margin: '0 auto' }}
              height="48"
              viewBox="0 0 400 48"
              fill="none"
            >
              <path
                className="path-line"
                d="M8 38 Q 120 8 200 22 T 392 30"
                stroke="#3346AC"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <circle cx="392" cy="30" r="4.5" fill="#3DA35D" className="animate-pulse" />
            </svg>
          </div>

          {/* Tagline */}
          <p
            className="mt-3 mb-7 max-w-3xl"
            style={{
              ...SORA,
              fontSize: 'clamp(1.15rem, 2.8vw, 1.55rem)',
              lineHeight: 1.35,
              fontWeight: 500,
              color: '#454652',
              ...fadeIn(320),
            }}
          >
            {isAr ? (
              <>اعرف <span style={{ color: '#3DA35D', fontWeight: 700 }}>مسارك</span>. اختر <span style={{ color: '#3DA35D', fontWeight: 700 }}>طريقك</span>.</>
            ) : (
              <>Connaître votre <span style={{ color: '#3DA35D', fontWeight: 700 }}>trajectoire</span>. Choisir votre <span style={{ color: '#3DA35D', fontWeight: 700 }}>chemin</span>.</>
            )}
          </p>

          {/* CTA buttons */}
          <div
            className="flex flex-col sm:flex-row gap-5"
            style={fadeIn(500)}
          >
            <Link
              to="/register"
              className="group btn-cta-primary flex items-center justify-center gap-3 px-10 py-4 rounded-xl font-semibold text-lg"
              style={INTER}
            >
              {isAr ? 'ابدأ التشخيص' : 'Commencer le diagnostic'}
              <ArrowRight
                size={20}
                className="group-hover:translate-x-1 transition-transform duration-200"
                style={isAr ? { transform: 'scaleX(-1)' } : {}}
              />
            </Link>
            <Link
              to="/login"
              className="btn-cta-secondary flex items-center justify-center px-10 py-4 rounded-xl font-semibold text-lg"
              style={INTER}
            >
              {t.landing.cta_login}
            </Link>
          </div>

          {/* ── Features section ── */}
          <div
            className="mt-16 w-full"
            style={{
              opacity:    ready ? 1 : 0,
              transition: 'opacity 1s ease 800ms',
            }}
          >
            <h2
              className="font-bold mb-8 text-center"
              style={{
                ...SORA,
                fontSize: 'clamp(1.5rem, 3.5vw, 2.1rem)',
                color: '#081F5C',
                lineHeight: 1.25,
              }}
            >
              {isAr
                ? 'أدوات ذكية لمستقبل ريادي'
                : 'Des outils intelligents pour un avenir entrepreneurial'}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  icon: <BarChart3 size={26} />,
                  title:   isAr ? 'تشخيص النمو'         : 'Diagnostic de Croissance',
                  desc:    isAr
                    ? 'تقييم شامل لأداء مشروعك باستخدام خوارزميات الذكاء الاصطناعي لتحديد نقاط القوة وفرص التحسين.'
                    : "Une évaluation complète de la performance de votre entreprise utilisant des algorithmes d'IA avancés pour identifier les points forts et les opportunités d'amélioration.",
                },
                {
                  icon: <Network size={26} />,
                  title:   isAr ? 'خريطة المنظومة'      : "Cartographie de l'Écosystème",
                  desc:    isAr
                    ? 'خريطة تفاعلية شاملة تربطك بالمستثمرين والحاضنات والشركاء الاستراتيجيين داخل تونس وخارجها.'
                    : "Une carte interactive complète vous connectant aux investisseurs, incubateurs et partenaires stratégiques au sein et en dehors de la Tunisie.",
                },
                {
                  icon: <Sparkles size={26} />,
                  title:   isAr ? 'توصيات مخصصة'        : 'Recommandations Personnalisées',
                  desc:    isAr
                    ? 'مسارات نمو مصممة خصيصاً بناءً على مرحلة نضج مشروعك وقطاعك التكنولوجي أو الصناعي.'
                    : "Des parcours de croissance sur mesure basés sur le stade de maturité de votre entreprise et votre secteur technologique ou industriel.",
                },
              ].map(({ icon, title, desc }, i) => (
                <div
                  key={i}
                  className="glass-card rounded-2xl p-8 flex flex-col gap-4 hover:shadow-xl transition-all duration-300 cursor-pointer group"
                  style={{ textAlign: isAr ? 'right' : 'left' }}
                >
                  {/* Icon + green dot */}
                  <div className="relative self-start">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center"
                      style={{ backgroundColor: '#dee0ff', color: '#3346AC' }}
                    >
                      {icon}
                    </div>
                    <span
                      className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: '#3DA35D' }}
                    />
                  </div>

                  <h3
                    className="font-semibold text-lg leading-snug"
                    style={{ ...SORA, color: '#081F5C' }}
                  >
                    {title}
                  </h3>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ ...INTER, color: '#454652' }}
                  >
                    {desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer
        className="w-full py-20 px-6 md:px-16 mt-12"
        style={{ backgroundColor: '#f0f3ff', borderTop: '1px solid rgba(197,197,213,0.18)' }}
      >
        <div className="max-w-container mx-auto flex flex-col items-center gap-12">

          {/* Partners heading */}
          <div className="text-center">
            <p
              className="text-xs font-semibold tracking-widest uppercase mb-3"
              style={{ ...INTER, color: 'rgba(69,70,82,0.55)' }}
            >
              {isAr ? 'بدعم من رواد المنظومة' : "Propulsé par des leaders de l'écosystème"}
            </p>
            <div className="w-12 h-1 mx-auto rounded-full" style={{ backgroundColor: '#006d33' }} />
          </div>

          {/* Partner logo placeholders */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-6 w-full">
            {PARTNERS.map((n) => (
              <div
                key={n}
                className="h-16 flex items-center justify-center grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-300 cursor-pointer"
              >
                <div
                  className="w-full h-full rounded-lg border border-dashed flex items-center justify-center text-xs font-semibold"
                  style={{ ...INTER, backgroundColor: '#dee8ff', borderColor: '#c5c5d5', color: '#757684' }}
                >
                  Partner {n}
                </div>
              </div>
            ))}
          </div>

          {/* Bottom footer bar */}
          <div
            className="w-full pt-12 mt-4 flex flex-col md:flex-row justify-between items-center gap-6"
            style={{ borderTop: '1px solid rgba(197,197,213,0.18)' }}
          >
            <span className="font-bold text-2xl" style={{ ...SORA, color: '#162c94' }}>Massar</span>

            <nav className="flex flex-wrap justify-center gap-6">
              {(isAr
                ? ['التأثير البيئي', 'ملاحظات قانونية', 'الخصوصية', 'الشروط العامة']
                : ['Impact Environnemental', 'Mentions Légales', 'Confidentialité', 'Conditions Générales']
              ).map((label) => (
                <a
                  key={label}
                  href="#"
                  className="text-sm transition-colors hover:text-primary-mid"
                  style={{ ...INTER, color: '#454652' }}
                >
                  {label}
                </a>
              ))}
            </nav>

            <p className="text-xs" style={{ ...INTER, color: 'rgba(69,70,82,0.55)' }}>
              © 2024 Massar.{' '}
              {isAr ? 'جميع الحقوق محفوظة.' : 'Tous droits réservés.'}
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
