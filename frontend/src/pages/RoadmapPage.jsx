import React, { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { useLang } from '../context/LanguageContext';
import { useAuth } from '../context/AuthContext';
import { useActiveProfile } from '../hooks/useActiveProfile';
import { roadmapApi } from '../api/roadmap';
import SiteHeader from '../components/SiteHeader';
import SiteFooter from '../components/SiteFooter';
import {
  ClipboardCheck, Landmark, Target, Users, FileBadge,
  ChevronDown, X, Send, ExternalLink, Sparkles, MapPin,
  TrendingUp, RefreshCw, Bot, Download,
} from "lucide-react";

// ─── Design tokens ────────────────────────────────────────────────────────
const BRAND = {
  navy:       "#1B2B6B",
  navyLight:  "#2D3F8A",
  navyXLight: "#EEF1FA",
  green:      "#2F6B5E",
  greenLight: "#DDEAE5",
  sand:       "#F5F7FF",
  border:     "#E2E6F0",
  borderSoft: "#EEF1FA",
  text:       "#0F1C45",
  textMid:    "#4A5475",
  textSoft:   "#8A90AA",
  white:      "#FFFFFF",
  road:       "#2C2C3A",
  roadLine:   "#FFFFFF",
};

const FONT  = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
const SERIF = "Georgia, 'Times New Roman', serif";

const HORIZON_META = {
  "Horizon 1": { label: "Immédiat",    accent: "#C0392B", soft: "#FBF0EC", glow: "rgba(192,57,43,0.18)" },
  "Horizon 2": { label: "Court terme", accent: BRAND.navy, soft: BRAND.navyXLight, glow: "rgba(27,43,107,0.18)" },
  "Horizon 3": { label: "Moyen terme", accent: BRAND.green, soft: BRAND.greenLight, glow: "rgba(47,107,94,0.18)" },
};

const MOMENTUM_LABELS = {
  stagnant:     { label: "Stagnant",           color: BRAND.textSoft, bg: "#F0F0F5" },
  steady:       { label: "Constant",           color: BRAND.green,    bg: BRAND.greenLight },
  accelerating: { label: "En Accélération 🚀", color: BRAND.navy,     bg: BRAND.navyXLight },
  breakthrough: { label: "Avancée Majeure 💎", color: "#C0392B",      bg: "#FBF0EC" },
};

const ICONS = {
  "clipboard-check":  ClipboardCheck,
  "building-bank":    Landmark,
  "target-arrow":     Target,
  "users-group":      Users,
  "file-certificate": FileBadge,
};

// The SVG road path — a winding S-curve across a 900×700 canvas
// Anchor points along the path are pre-computed in ROAD_STOPS below
const ROAD_PATH = "M 60,80 C 160,80 200,200 300,220 C 400,240 440,160 540,180 C 640,200 660,320 760,340 C 840,355 880,440 840,520 C 800,600 700,620 620,640 C 540,660 460,600 380,620 C 300,640 220,700 140,680";

// 8 evenly-distributed t-values along the path for up to 8 stops
// Each entry: { t: 0–1 along path, side: "left"|"right" for card placement }
const STOP_CONFIGS = [
  { t: 0.04, side: "right" },
  { t: 0.16, side: "left"  },
  { t: 0.29, side: "right" },
  { t: 0.42, side: "left"  },
  { t: 0.55, side: "right" },
  { t: 0.67, side: "left"  },
  { t: 0.79, side: "right" },
  { t: 0.91, side: "left"  },
];

function groupByHorizon(steps) {
  if (!steps) return [];
  const order = ["Horizon 1", "Horizon 2", "Horizon 3"];
  return order
    .map((h) => ({ horizon: h, items: steps.filter((s) => s.time_horizon === h) }))
    .filter((g) => g.items.length > 0);
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE
// ═══════════════════════════════════════════════════════════════════════════
export default function RoadmapPage() {
  const { token }   = useAuth();
  const { profile } = useActiveProfile();
  const { isAr }    = useLang();

  const [roadmap,            setRoadmap]            = useState(null);
  const [loadingRoadmap,     setLoadingRoadmap]     = useState(false);
  const [errorState,         setErrorState]         = useState(null);
  const [needsGeneration,    setNeedsGeneration]    = useState(false);

  const [currentScore,       setCurrentScore]       = useState(56);
  const [momentum,           setMomentum]           = useState("steady");
  const [evaluationFeedback, setEvaluationFeedback] = useState("");
  const [progressInput,      setProgressInput]      = useState("");
  const [isEvaluating,       setIsEvaluating]       = useState(false);

  const [chatOpen,      setChatOpen]      = useState(false);
  const [chatStep,      setChatStep]      = useState(null);
  const [chatSessionId, setChatSessionId] = useState(null);
  const [chatMessages,  setChatMessages]  = useState([]);
  const [chatInput,     setChatInput]     = useState("");
  const [isSending,     setIsSending]     = useState(false);

  const [openStepId, setOpenStepId] = useState(null);
  const panelRefs = useRef({});

  useEffect(() => {
    if (token && profile?.id) fetchRoadmap();
  }, [token, profile?.id]);

  async function fetchRoadmap() {
    setLoadingRoadmap(true); setErrorState(null); setNeedsGeneration(false);
    try {
      const res = await roadmapApi.get(token, profile.id);
      if (res && res.status === "success") setRoadmap(res.data);
      else setNeedsGeneration(true);
    } catch { setNeedsGeneration(true); }
    finally { setLoadingRoadmap(false); }
  }

  async function triggerRoadmapGeneration() {
    if (!profile?.id) return;
    setLoadingRoadmap(true); setErrorState(null);
    try {
      const res = await roadmapApi.generate(token, profile.id);
      if (res && res.status === "success") { setRoadmap(res.data); setNeedsGeneration(false); }
      else throw new Error("Impossible de générer le parcours.");
    } catch (err) {
      setErrorState(err.message || "Erreur lors de la génération.");
    } finally { setLoadingRoadmap(false); }
  }

  async function handleEvaluateProgress(e) {
    e.preventDefault();
    if (!progressInput.trim() || isEvaluating || !profile?.id) return;
    const currentUpdate = progressInput.trim();
    setIsEvaluating(true); setEvaluationFeedback("");
    try {
      const res = await roadmapApi.evaluateProgress(token, { profileId: profile.id, latestUpdate: currentUpdate });
      if (res && res.status === "success") {
        setCurrentScore(res.data.progress_score || 65);
        setMomentum(res.data.momentum || "accelerating");
        setEvaluationFeedback(res.data.reasoning);
        setProgressInput("");
      } else setEvaluationFeedback("Une erreur est survenue lors de l'évaluation.");
    } catch { setEvaluationFeedback("Impossible de joindre le moteur d'évaluation."); }
    finally { setIsEvaluating(false); }
  }

  function handleStepClick(e, step) {
    const stepIdStr = String(step.id);
    if (e.ctrlKey || e.metaKey) {
      setChatStep(step);
      setChatSessionId(`session_${stepIdStr}_${Date.now()}`);
      setChatMessages([{
        role: "assistant",
        content: `Posez une question sur « ${step.title} » — je répondrai en me basant uniquement sur votre diagnostic, vos scores et les sources citées pour cette étape.`,
      }]);
      setChatOpen(true);
      return;
    }
    setOpenStepId((cur) => (cur === stepIdStr ? null : stepIdStr));
  }

  async function handleSendMessage() {
    if (!chatInput.trim() || isSending || !profile?.id) return;
    const userText = chatInput.trim();
    setChatInput("");
    setIsSending(true);
    setChatMessages((prev) => [...prev, { role: "user", content: userText }]);
    try {
      const res = await roadmapApi.chat(token, {
        sessionId: chatSessionId,
        profileId: profile.id,
        component: { title: chatStep.title, description: chatStep.explanation || "", step_id: String(chatStep.id) },
        message: userText,
      });
      if (res && res.status === "success")
        setChatMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
      else
        setChatMessages((prev) => [...prev, { role: "assistant", content: "Désolé, une erreur est survenue." }]);
    } catch {
      setChatMessages((prev) => [...prev, { role: "assistant", content: "Impossible de joindre le serveur." }]);
    } finally { setIsSending(false); }
  }

  const roadmapData = roadmap?.data || roadmap;
  console.log("Roadmap data:", roadmapData);
  console.log("extracting to groups");
  console.log("Roadmap steps:", roadmapData?.steps);

  // Flatten all steps in order for the road (preserving horizon grouping for colours)
  const allSteps = useMemo(() => {
    const steps = roadmapData?.steps || [];
    return steps.map((s) => ({
      ...s,
      horizonMeta: HORIZON_META[s.time_horizon] || HORIZON_META["Horizon 1"],
    }));
  }, [roadmapData]);

  const groups = useMemo(() => groupByHorizon(roadmapData?.steps), [roadmapData]);

  useEffect(() => {
    if (openStepId && panelRefs.current[openStepId])
      panelRefs.current[openStepId].scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [openStepId]);

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: BRAND.sand, fontFamily: FONT }}>
      <SiteHeader />

      <main style={{ flex: 1, display: "flex", width: "100%" }}>
        {loadingRoadmap ? (
          <CenteredState>
            <div style={{ width: 56, height: 56, borderRadius: "50%", background: BRAND.navyXLight, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
              <RefreshCw size={24} color={BRAND.navy} style={{ animation: "spin 1.4s linear infinite" }} />
            </div>
            <p style={{ color: BRAND.textMid, fontSize: 15, margin: 0 }}>Synchronisation avec votre feuille de route…</p>
          </CenteredState>

        ) : errorState ? (
          <CenteredState>
            <div style={{ width: 56, height: 56, borderRadius: "50%", background: "#FBF0EC", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
              <X size={24} color="#C0392B" />
            </div>
            <p style={{ color: "#C0392B", fontWeight: 700, fontSize: 17, margin: "0 0 8px" }}>Échec de synchronisation</p>
            <p style={{ color: BRAND.textMid, fontSize: 14, margin: "0 0 24px", maxWidth: 400, textAlign: "center" }}>{errorState}</p>
            <PrimaryButton onClick={fetchRoadmap}>Réessayer</PrimaryButton>
          </CenteredState>

        ) : needsGeneration ? (
          <CenteredState>
            <div style={{ width: 70, height: 70, borderRadius: 20, background: BRAND.navyXLight, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 24 }}>
              <Sparkles size={32} color={BRAND.navy} />
            </div>
            <h2 style={{ fontFamily: SERIF, fontSize: 28, fontWeight: 700, color: BRAND.text, margin: "0 0 10px", textAlign: "center" }}>
              Générez votre plan d'action
            </h2>
            <p style={{ color: BRAND.textMid, fontSize: 14, maxWidth: 460, marginBottom: 28, textAlign: "center", lineHeight: 1.6 }}>
              Prêt à transformer votre diagnostic en jalons clairs et actionnables adaptés à l'écosystème tunisien ?
            </p>
            <PrimaryButton onClick={triggerRoadmapGeneration}>
              Générer mon parcours <TrendingUp size={16} style={{ marginLeft: 6 }} />
            </PrimaryButton>
          </CenteredState>

        ) : (
          <div style={{ flex: 1, maxWidth: chatOpen ? "calc(100% - 400px)" : "100%", transition: "max-width 0.3s ease", padding: "48px 40px 96px", boxSizing: "border-box" }}>
            <div style={{ maxWidth: 960, margin: "0 auto" }}>

              <PageHeader stage={roadmapData?.maturity_stage || "Analyse..."} score={currentScore} momentum={momentum} />

              <ProgressEvaluator
                input={progressInput}
                setInput={setProgressInput}
                onSubmit={handleEvaluateProgress}
                loading={isEvaluating}
                feedback={evaluationFeedback}
              />

              <HorizonLegend groups={groups} />

              {/* ── WINDING ROAD ── */}
              <WindingRoad
                steps={allSteps}
                openStepId={openStepId}
                onStepClick={handleStepClick}
                panelRefs={panelRefs}
              />

              <Footnote />
            </div>
          </div>
        )}

        {chatOpen && (
          <SideChat
            step={chatStep}
            messages={chatMessages}
            onClose={() => setChatOpen(false)}
            chatInput={chatInput}
            setChatInput={setChatInput}
            onSend={handleSendMessage}
            isSending={isSending}
          />
        )}
      </main>

      <SiteFooter />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// WINDING ROAD  — the centrepiece visual
// ═══════════════════════════════════════════════════════════════════════════

function WindingRoad({ steps, openStepId, onStepClick, panelRefs }) {
  const svgRef = useRef(null);
  const [stopPoints, setStopPoints] = useState([]);

  // Compute pixel coordinates for each stop along the SVG path
  const computeStops = useCallback(() => {
    const pathEl = svgRef.current?.querySelector("#road-centerline");
    if (!pathEl || steps.length === 0) return;
    const total = pathEl.getTotalLength();
    const pts = steps.slice(0, STOP_CONFIGS.length).map((step, i) => {
      const cfg = STOP_CONFIGS[i];
      const pt  = pathEl.getPointAtLength(cfg.t * total);
      return { x: pt.x, y: pt.y, side: cfg.side, step };
    });
    setStopPoints(pts);
  }, [steps]);

  useEffect(() => {
    // Wait one frame for the SVG to be in the DOM
    const raf = requestAnimationFrame(computeStops);
    return () => cancelAnimationFrame(raf);
  }, [computeStops]);

  // SVG viewport dimensions
  const VW = 900, VH = 720;
  // Road width (the dark tarmac band)
  const ROAD_W = 72;

  return (
    <div style={{ position: "relative", width: "100%", marginTop: 32, marginBottom: 24 }}>
      {/* ── SVG road layer ── */}
      <svg
        ref={svgRef}
        viewBox={`0 0 ${VW} ${VH}`}
        style={{ width: "100%", height: "auto", display: "block", overflow: "visible" }}
        aria-hidden="true"
      >
        <defs>
          <filter id="road-shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="6" stdDeviation="10" floodColor="rgba(0,0,0,0.18)" />
          </filter>
        </defs>

        {/* Shadow under road */}
        <path
          d={ROAD_PATH}
          fill="none"
          stroke="rgba(0,0,0,0.12)"
          strokeWidth={ROAD_W + 14}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Tarmac */}
        <path
          d={ROAD_PATH}
          fill="none"
          stroke={BRAND.road}
          strokeWidth={ROAD_W}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dashed centre line */}
        <path
          d={ROAD_PATH}
          fill="none"
          stroke={BRAND.roadLine}
          strokeWidth={3}
          strokeLinecap="round"
          strokeDasharray="18 14"
          opacity={0.35}
        />
        {/* Invisible path used only for getPointAtLength() */}
        <path id="road-centerline" d={ROAD_PATH} fill="none" stroke="none" />

        {/* Stop dots on the road */}
        {stopPoints.map(({ x, y, step }, i) => {
          const meta     = step.horizonMeta;
          const isOpen   = openStepId === String(step.id);
          return (
            <g key={step.id} style={{ cursor: "pointer" }} onClick={(e) => onStepClick(e, step)}>
              {/* Outer glow ring when active */}
              {isOpen && (
                <circle cx={x} cy={y} r={26} fill={meta.glow} />
              )}
              {/* White border ring */}
              <circle cx={x} cy={y} r={20} fill={BRAND.white} />
              {/* Coloured fill */}
              <circle cx={x} cy={y} r={17} fill={isOpen ? meta.accent : BRAND.white} stroke={meta.accent} strokeWidth={2.5} />
              {/* Step number */}
              <text x={x} y={y + 5} textAnchor="middle" fontSize={12} fontWeight={700} fill={isOpen ? BRAND.white : meta.accent} fontFamily={FONT}>
                {String(i + 1).padStart(2, "0")}
              </text>
              {/* Stem line to card */}
              <StemLine x={x} y={y} side={stopPoints[i]?.side} />
            </g>
          );
        })}
      </svg>

      {/* ── Floating step cards (absolutely positioned over SVG) ── */}
      {stopPoints.map(({ x, y, side, step }, i) => {
        const meta   = step.horizonMeta;
        const isOpen = openStepId === String(step.id);
        const Icon   = ICONS[step.icon] || ClipboardCheck;

        // Convert SVG units → % of container width/height
        const leftPct = (x / VW) * 100;
        const topPct  = (y / VH) * 100;

        // Cards sit to the left or right of the stop dot
        const cardStyle = {
          position: "absolute",
          top:  `${topPct}%`,
          left: side === "right" ? `${leftPct + 4}%` : undefined,
          right: side === "left" ? `${100 - leftPct + 4}%` : undefined,
          transform: "translateY(-50%)",
          width: 230,
          zIndex: isOpen ? 20 : 10,
        };

        return (
          <div key={step.id} style={cardStyle} ref={(el) => (panelRefs.current[String(step.id)] = el)}>
            {/* Collapsed card */}
            <button
              onClick={(e) => onStepClick(e, step)}
              style={{
                all: "unset",
                display: "flex",
                alignItems: "center",
                gap: 10,
                width: "100%",
                cursor: "pointer",
                background: BRAND.white,
                border: `2px solid ${isOpen ? meta.accent : BRAND.border}`,
                borderRadius: 14,
                padding: "10px 14px",
                boxSizing: "border-box",
                boxShadow: isOpen
                  ? `0 6px 24px ${meta.glow}`
                  : "0 2px 10px rgba(27,43,107,0.08)",
                transition: "all 0.2s",
              }}
            >
              <div style={{
                width: 34, height: 34, borderRadius: 10, flexShrink: 0,
                background: isOpen ? meta.accent : meta.soft,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Icon size={17} color={isOpen ? BRAND.white : meta.accent} strokeWidth={1.8} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: meta.accent, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>
                  {meta.label}
                </div>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: BRAND.text, lineHeight: 1.3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {step.title}
                </div>
              </div>
              <ChevronDown size={14} color={BRAND.textSoft} style={{ flexShrink: 0, transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
            </button>

            {/* Expanded detail panel */}
            {isOpen && (
              <div style={{
                marginTop: 8,
                background: BRAND.white,
                border: `1.5px solid ${meta.accent}`,
                borderRadius: 14,
                padding: "14px 16px",
                boxShadow: `0 8px 28px ${meta.glow}`,
                fontSize: 13,
                color: BRAND.textMid,
                lineHeight: 1.65,
              }}>
                <p style={{ margin: "0 0 12px", whiteSpace: "pre-wrap" }}>{step.explanation}</p>

                {step.status && (
                  <div style={{ fontSize: 11, color: BRAND.textSoft, marginBottom: 12 }}>
                    Statut : <span style={{ color: BRAND.navy, fontWeight: 600 }}>{step.status}</span>
                  </div>
                )}

                {step.resources && step.resources.length > 0 && (
                  <div style={{ borderTop: `1px solid ${BRAND.borderSoft}`, paddingTop: 10, display: "flex", flexDirection: "column", gap: 7 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: meta.accent, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>
                      Ressources
                    </div>
                    {step.resources.map((res, ri) => (
                      <div key={ri} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, background: meta.soft, borderRadius: 8, padding: "7px 10px" }}>
                        <span style={{ fontSize: 11.5, fontWeight: 500, color: BRAND.text, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {res.title || "Lien utile"}
                        </span>
                        {res.link && (
                          <a href={res.link} target="_blank" rel="noreferrer"
                            style={{ color: meta.accent, display: "flex", alignItems: "center", gap: 3, fontSize: 11, fontWeight: 600, textDecoration: "none", flexShrink: 0 }}
                          >
                            <ExternalLink size={11} />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ fontSize: 10.5, color: BRAND.textSoft, marginTop: 10, fontStyle: "italic" }}>
                  Ctrl + clic → assistant contextuel
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Tiny SVG line from the road dot to where the card sits
function StemLine({ x, y, side }) {
  const dx = side === "right" ? 38 : -38;
  return (
    <line
      x1={x} y1={y}
      x2={x + dx} y2={y}
      stroke={BRAND.textSoft}
      strokeWidth={1.5}
      strokeDasharray="4 3"
      opacity={0.6}
    />
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SHARED ATOMS
// ═══════════════════════════════════════════════════════════════════════════

function CenteredState({ children }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 48 }}>
      {children}
    </div>
  );
}

function PrimaryButton({ onClick, children, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: disabled ? BRAND.textSoft : BRAND.navy,
      color: BRAND.white, border: "none", borderRadius: 10,
      padding: "12px 26px", fontSize: 14, fontWeight: 600,
      cursor: disabled ? "default" : "pointer",
      display: "inline-flex", alignItems: "center", gap: 6,
      fontFamily: FONT, letterSpacing: "0.01em", transition: "background 0.15s",
    }}>
      {children}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PAGE HEADER
// ═══════════════════════════════════════════════════════════════════════════

function PageHeader({ stage, score, momentum }) {
  const mMeta = MOMENTUM_LABELS[momentum] || MOMENTUM_LABELS.steady;
  return (
    <div style={{
      background: BRAND.white, borderRadius: 18, border: `1px solid ${BRAND.border}`,
      padding: "28px 32px", marginBottom: 24,
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      flexWrap: "wrap", gap: 20, boxShadow: "0 2px 12px rgba(27,43,107,0.06)",
    }}>
      <div>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6,
          fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase",
          color: BRAND.navy, fontWeight: 700, marginBottom: 10,
          background: BRAND.navyXLight, padding: "4px 10px", borderRadius: 20,
        }}>
          <MapPin size={12} strokeWidth={2.5} />
          Stade · {stage}
        </div>
        <h1 style={{ fontFamily: SERIF, fontSize: 30, fontWeight: 700, color: BRAND.text, margin: 0 }}>
          Votre feuille de route
        </h1>
        <p style={{ fontSize: 13, color: BRAND.textMid, margin: "6px 0 0", lineHeight: 1.5 }}>
          Cliquez sur une étape pour voir les détails.{" "}
          <span style={{ color: BRAND.navy, fontWeight: 600 }}>Ctrl + clic pour discuter.</span>
        </p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 11.5, color: BRAND.textSoft, fontWeight: 500, marginBottom: 2 }}>Score d'exécution</div>
          <div style={{ fontSize: 34, fontWeight: 800, color: BRAND.navy, lineHeight: 1 }}>
            {score}<span style={{ fontSize: 14, color: BRAND.textSoft, fontWeight: 400 }}> /100</span>
          </div>
        </div>
        <div style={{ background: mMeta.bg, color: mMeta.color, fontSize: 12, fontWeight: 600, padding: "5px 12px", borderRadius: 20 }}>
          {mMeta.label}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PROGRESS EVALUATOR
// ═══════════════════════════════════════════════════════════════════════════

function ProgressEvaluator({ input, setInput, onSubmit, loading, feedback }) {
  return (
    <div style={{ background: BRAND.white, padding: "22px 28px", borderRadius: 16, border: `1px solid ${BRAND.border}`, marginBottom: 28, boxShadow: "0 1px 6px rgba(27,43,107,0.04)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <TrendingUp size={15} color={BRAND.navy} strokeWidth={2.2} />
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: BRAND.text }}>Console d'évaluation continue</h3>
      </div>
      <p style={{ fontSize: 12.5, color: BRAND.textMid, margin: "0 0 16px", lineHeight: 1.55 }}>
        Décrivez vos récentes avancées. L'évaluateur recalculera dynamiquement vos scores.
      </p>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 10 }}>
        <input
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Ex : J'ai finalisé le dépôt du dossier de brevet à l'INNORPI…"
          style={{ flex: 1, padding: "10px 14px", borderRadius: 10, border: `1px solid ${BRAND.border}`, fontSize: 13.5, background: BRAND.sand, color: BRAND.text, outline: "none", fontFamily: FONT }}
        />
        <button type="submit" disabled={!input.trim() || loading} style={{
          background: (!input.trim() || loading) ? BRAND.textSoft : BRAND.navy,
          color: BRAND.white, border: "none", borderRadius: 10,
          padding: "0 22px", fontSize: 13.5, fontWeight: 600,
          cursor: (!input.trim() || loading) ? "default" : "pointer",
          display: "flex", alignItems: "center", gap: 8, fontFamily: FONT,
        }}>
          {loading ? <RefreshCw size={14} style={{ animation: "spin 1.4s linear infinite" }} /> : <TrendingUp size={14} />}
          Évaluer
        </button>
      </form>
      {feedback && (
        <div style={{ marginTop: 14, padding: "12px 16px", background: BRAND.navyXLight, borderLeft: `3px solid ${BRAND.navy}`, borderRadius: "0 10px 10px 0", fontSize: 13, color: BRAND.textMid, lineHeight: 1.6 }}>
          <strong style={{ color: BRAND.navy }}>Analyse :</strong> {feedback}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// HORIZON LEGEND
// ═══════════════════════════════════════════════════════════════════════════

function HorizonLegend({ groups }) {
  return (
    <div style={{ display: "flex", gap: 20, flexWrap: "wrap", paddingBottom: 14, marginBottom: 4 }}>
      {Object.entries(HORIZON_META).map(([key, meta]) => (
        <div key={key} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, fontWeight: 600, color: BRAND.textMid }}>
          <span style={{ width: 10, height: 10, borderRadius: "50%", background: meta.accent, display: "inline-block" }} />
          {meta.label}
        </div>
      ))}
      <span style={{ marginLeft: "auto", fontSize: 12, color: BRAND.textSoft, fontStyle: "italic", alignSelf: "center" }}>
        Ctrl + clic sur une étape pour ouvrir l'assistant
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// SIDE CHAT
// ═══════════════════════════════════════════════════════════════════════════

function SideChat({ step, messages, onClose, chatInput, setChatInput, onSend, isSending }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  return (
    <div style={{
      width: 400, flexShrink: 0,
      height: "calc(100vh - 70px)", position: "sticky", top: 70,
      background: BRAND.white, borderLeft: `1px solid ${BRAND.border}`,
      display: "flex", flexDirection: "column",
      boxShadow: "-4px 0 24px rgba(27,43,107,0.08)",
    }}>
      {/* Header */}
      <div style={{ padding: "18px 20px", borderBottom: `1px solid ${BRAND.borderSoft}`, display: "flex", alignItems: "center", justifyContent: "space-between", background: BRAND.navyXLight }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: BRAND.navy, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Bot size={18} color={BRAND.white} strokeWidth={1.8} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: BRAND.text }}>Assistant Contextuel</div>
            <div style={{ fontSize: 11.5, color: BRAND.textSoft, marginTop: 1 }}>
              Focus : <span style={{ color: BRAND.navy, fontWeight: 600 }}>{step?.title}</span>
            </div>
          </div>
        </div>
        <button onClick={onClose} style={{ all: "unset", cursor: "pointer", color: BRAND.textSoft, width: 30, height: 30, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <X size={17} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{ flex: 1, padding: "16px 16px 8px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ alignSelf: msg.role === "user" ? "flex-end" : "flex-start", maxWidth: "86%" }}>
            <div style={{
              background: msg.role === "user" ? BRAND.navy : BRAND.navyXLight,
              color: msg.role === "user" ? BRAND.white : BRAND.text,
              padding: "11px 15px",
              borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "4px 14px 14px 14px",
              fontSize: 13.5, lineHeight: 1.6, whiteSpace: "pre-wrap",
              boxShadow: msg.role === "user" ? "0 2px 10px rgba(27,43,107,0.18)" : "none",
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {isSending && (
          <div style={{ alignSelf: "flex-start", display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", background: BRAND.navyXLight, borderRadius: "4px 14px 14px 14px" }}>
            <RefreshCw size={13} color={BRAND.navy} style={{ animation: "spin 1.4s linear infinite" }} />
            <span style={{ fontSize: 12.5, color: BRAND.navy, fontStyle: "italic" }}>Analyse du contexte…</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ padding: "12px 16px", borderTop: `1px solid ${BRAND.borderSoft}` }}>
        <form onSubmit={(e) => { e.preventDefault(); onSend(); }} style={{ display: "flex", gap: 8, border: `1.5px solid ${BRAND.border}`, borderRadius: 13, padding: "7px 8px 7px 14px", alignItems: "center", background: BRAND.sand }}>
          <input
            value={chatInput} onChange={(e) => setChatInput(e.target.value)}
            disabled={isSending} placeholder="Votre question…"
            style={{ flex: 1, border: "none", outline: "none", fontSize: 13.5, background: "transparent", color: BRAND.text, fontFamily: FONT }}
          />
          <button type="submit" disabled={!chatInput.trim() || isSending} style={{
            all: "unset",
            background: (!chatInput.trim() || isSending) ? BRAND.textSoft : BRAND.navy,
            width: 32, height: 32, borderRadius: 9,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: (!chatInput.trim() || isSending) ? "default" : "pointer", flexShrink: 0,
          }}>
            <Send size={14} color={BRAND.white} strokeWidth={2} />
          </button>
        </form>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// FOOTNOTE
// ═══════════════════════════════════════════════════════════════════════════

function Footnote() {
  return (
    <div style={{ marginTop: 40, paddingTop: 20, borderTop: `1px solid ${BRAND.border}`, fontSize: 12, color: BRAND.textSoft, lineHeight: 1.7 }}>
      Chaque étape est générée à partir de votre diagnostic, de vos scores et d'extraits récupérés dans la base de connaissances — aucune ressource n'est inventée par le modèle.
    </div>
  );
}