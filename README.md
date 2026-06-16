# 🇹🇳 AINS 2026 — Plateforme IA pour l'Entrepreneuriat

> Une plateforme IA qui dit aux entrepreneurs tunisiens exactement 
> où en est leur projet, pourquoi, et quoi faire ensuite —
> dans leur langue.

**AINS Hackathon 2026** — Organisé par PNUD, GEWEET, ODC, IEEE, APII et AINS 4.0

---

## Problème

Les entrepreneurs en Tunisie font face à trois échecs structurels :

1. **Ils ne savent pas où ils en sont réellement** — ils surestiment 
   la maturité de leur projet (ex: se croire prêt au financement 
   sans modèle validé)
2. **Les outils existants répondent mais ne diagnostiquent pas** — 
   guides statiques, chatbots génériques, portails déconnectés
3. **Les ressources sont fragmentées et jamais personnalisées** — 
   aucun outil ne connecte les gaps réels d'un entrepreneur aux 
   programmes tunisiens disponibles

---

## Notre Solution

Une plateforme unifiée articulée autour de trois modules intégrés :

### Module 1 — Moteur de Diagnostic Adaptatif
Questionnaire dynamique dont les questions évoluent selon les 
réponses. Classifie le projet parmi 6 stades de maturité et détecte 
l'écart entre la perception de l'entrepreneur et la réalité.

### Module 2 — Scoring Multi-Dimensionnel Explicable
5 scores composites (Marché, Offre Commerciale, Innovation, 
Scalabilité, Green) avec sous-critères pondérés, justifications 
en langage naturel et détection d'anomalies.
Le Green Score suit exactement le référentiel PNUD présenté 
lors du workshop AINS 2026.

### Module 3 — Roadmap RAG & Orientation Ressources
Plan d'action personnalisé ancré dans une base de connaissances 
de 41+ ressources tunisiennes réelles. Chaque recommandation 
cite sa source. Aucune hallucination possible.

### Bonus — Assistant Vocal Trilingue
Assistant conversationnel en Français, Arabe et Darija Tunisienne,
ancré dans les outputs du diagnostic et de la base de connaissances.

---

##  Architecture

[React Dashboard]

│

▼

[Project Profile Store — SQLite]

│

├──► [Diagnostic Engine] → classification + gap detection

│

├──► [Scoring Engine] → 5 scores + UNDP Green framework

│

└──► [RAG Pipeline — ChromaDB] → roadmap + resources

│

▼

[Claude API — Anthropic]

Trilingual FR/AR/Darija

---

## 🛠️ Stack Technique

| Couche | Technologie |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React + Tailwind CSS |
| LLM | Claude API (Anthropic) — claude-sonnet-4-6 |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers |
| Base de données | SQLite → PostgreSQL |
| Authentification | JWT + bcrypt |
| STT | OpenAI Whisper |
| TTS | Web Speech API |

---

##  Structure du Projet
/backend

/api          — routes FastAPI

/diagnostic   — moteur de diagnostic

/scoring      — moteur de scoring (5 dimensions)

/rag          — pipeline RAG + génération roadmap

/security     — JWT, middleware, rate limiting

/models       — schémas de données
/frontend

/src

/components — composants React

/pages      — Dashboard, Questionnaire, Chat
/data

/kb_structured   — 41+ ressources tunisiennes (JSON)

/taxonomy        — taxonomie des 6 stades + exemples labellisés

/evaluation      — protocole et résultats d'évaluation

/docs

SCORING_METHODOLOGY.md

ARCHITECTURE.md

DATA_CARD.md

API_CONTRACT.md

---

## 🗂️ Contributions Originales (Datasets)

- **Catalogue des programmes d'accompagnement tunisiens**
  41+ programmes structurés et vérifiés (JSON + CSV)
  
- **Taxonomie des stades de maturité**
  6 stades avec critères définis + 30 profils labellisés
  
- **Dataset Green Score**
  Profils environnementaux labellisés selon le référentiel PNUD

Tous les datasets sont open-source sous `/data`.

---

## ⚙️ Installation

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # ajouter votre clé Anthropic
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm start
```

---



## Protocole d'Évaluation

- **Classification accuracy** — 30 profils labellisés (5 par stade)
- **Precision@3** — pertinence des ressources récupérées sur 10 profils
- Résultats dans `/data/evaluation/`

---

##  Langues Supportées

- 🇫🇷 Français
- 🇸🇦 Arabe (MSA)
- 🇹🇳 Darija Tunisienne

---


