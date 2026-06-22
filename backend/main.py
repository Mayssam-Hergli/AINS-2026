from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

load_dotenv()

from database import init_db
from api.auth import router as auth_router
from api.profiles import router as profiles_router
from api.scoring import router as scoring_router

# ─── App Instance ────────────────────────────────────────────
app = FastAPI(
    title="AINS 2026 — Plateforme IA pour l'Entrepreneuriat",
    description="""
    Plateforme de diagnostic, scoring et orientation
    pour les entrepreneurs tunisiens.

    3 modules intégrés:
    - Moteur de diagnostic adaptatif (6 stades de maturité)
    - Scoring multi-dimensionnel explicable (5 dimensions)
    - RAG + Roadmap ancrée dans 41+ ressources tunisiennes réelles

    Assistant trilingue: Français / Arabe / Darija Tunisienne
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Rate Limiting ────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database init ────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_db()

# ─── Routers ──────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(scoring_router)

# ─── Health ───────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "platform": "AINS 2026 — Plateforme IA pour l'Entrepreneuriat",
        "status": "running",
        "version": "1.0.0",
        "modules": ["diagnostic", "scoring", "rag", "assistant"],
        "languages": ["fr", "ar", "tn"],
        "docs": "/docs",
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}

# ─── Diagnostic Routes (stub — owned by MS1) ─────────────────

@app.post("/diagnostic/start", tags=["Diagnostic"])
def start_diagnostic():
    """
    Démarre un nouveau diagnostic pour un entrepreneur.
    Retourne la première question adaptée à son profil.
    """
    return {"message": "diagnostic start — coming Day 2"}

@app.post("/diagnostic/answer", tags=["Diagnostic"])
def submit_answer():
    """
    Soumet une réponse et retourne la prochaine question.
    La logique de branchement adapte les questions selon les réponses précédentes.
    """
    return {"message": "diagnostic answer — coming Day 2"}

@app.get("/diagnostic/result/{profile_id}", tags=["Diagnostic"])
def get_diagnostic_result(profile_id: str):
    """
    Retourne le résultat complet du diagnostic:
    - Stade de maturité classifié
    - Gap perception vs réalité
    - Blockers identifiés et classés
    """
    return {"message": f"diagnostic result for {profile_id} — coming Day 2"}

# ─── RAG + Roadmap Routes (stub — owned by MS3) ──────────────

@app.post("/roadmap/generate/{profile_id}", tags=["RAG & Roadmap"])
def generate_roadmap(profile_id: str):
    """
    Génère une roadmap personnalisée ancrée dans la base de connaissances.
    Chaque recommandation cite sa source. Aucune hallucination possible.
    Horizons: immédiat / court terme / moyen terme.
    """
    return {"message": f"roadmap for {profile_id} — coming Day 3"}

@app.get("/roadmap/{profile_id}", tags=["RAG & Roadmap"])
def get_roadmap(profile_id: str):
    return {"message": f"get roadmap for {profile_id} — coming Day 3"}

# ─── Assistant Routes (stub) ──────────────────────────────────

@app.post("/assistant/chat", tags=["Assistant"])
def chat():
    """
    Assistant conversationnel trilingue (FR/AR/Darija).
    Ancré dans le profil diagnostic + scores + KB de l'entrepreneur.
    Jamais de réponses génériques — toujours contextualisé.
    """
    return {"message": "assistant chat — coming Day 3"}

@app.get("/assistant/history/{profile_id}", tags=["Assistant"])
def get_history(profile_id: str):
    return {"message": f"chat history for {profile_id} — coming Day 3"}
