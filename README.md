# Massar — مسار | Plateforme IA pour l'Entrepreneuriat

> Massar — مسار | Une plateforme IA qui dit aux entrepreneurs tunisiens exactement 
> où en est leur projet, pourquoi, et quoi faire ensuite —
> dans leur langue.

> *"Massar — Connaître votre trajectoire. Choisir votre chemin."*
> *"مسار — اعرف وين أنت. اختار وين تمشي."*

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

### Document Intelligence — Analyse de documents

L'entrepreneur peut soumettre des documents optionnellement lors du questionnaire :
business plan, relevés financiers, contrats signés, lettres d'intention, photos d'opérations.
La soumission n'est pas obligatoire — le système fonctionne sans, mais les résultats
sont plus précis avec.

Claude Vision API analyse chaque document et extrait les signaux pertinents :
chiffres d'affaires réels, preuves de traction, clauses contractuelles, état financier.
Ces signaux sont croisés avec les réponses déclarées dans le questionnaire.

Si l'entrepreneur déclare n'avoir aucun client mais soumet un contrat signé,
le système détecte la divergence et l'intègre dans le diagnostic et le scoring.

Formats acceptés : PDF, JPG, JPEG, PNG
Taille maximale : 10 MB par fichier
Traitement : Claude Vision API — extraction et structuration automatique

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

### Générateur de Rapport PDF

À la fin du parcours complet, la plateforme génère un rapport PDF professionnel
téléchargeable contenant :

- Stade de maturité diagnostiqué avec les preuves collectées
- Analyse de gap si auto-évaluation diverge du diagnostic
- 5 score cards avec sous-scores, pondérations et justifications
- Green Score PNUD avec détail par pilier et classification officielle
- Blockers prioritaires classés par domaine et sévérité
- Roadmap personnalisée avec horizons temporels
- Ressources recommandées avec sources et coordonnées
- Recommandations d'optimisation verte avec estimations de coût en TND

Ce rapport est le document que l'entrepreneur présente à une banque,
un incubateur, ou un programme de financement.

Généré avec : ReportLab
Langues : Français, Arabe MSA, Darija Tunisienne

---

## 🔒 Sécurité & Protection des Données

Les entrepreneurs partagent des données sensibles sur leur projet —
stratégie, finances, équipe, positionnement marché. Nous traitons
ces données avec des standards de production.

### Ce que nous protégeons
- Données business confidentielles (idées pré-lancement, financials)
- Profils entrepreneurs et historique de diagnostic
- Réponses au questionnaire et scores

### Couches de sécurité implémentées

| Couche | Implémentation | Protection |
|---|---|---|
| Authentification | JWT + bcrypt | Sessions sécurisées, mots de passe hashés |
| Isolation des données | Scoping par user_id | Un utilisateur ne voit jamais les données d'un autre |
| Chiffrement transit | HTTPS enforced | Toutes les communications chiffrées |
| Chiffrement repos | AES-256 sur champs sensibles | Données illisibles en cas de breach DB |
| Rate limiting | slowapi (par IP + par user) | Protection contre spam et brute force |
| CORS | Origine frontend uniquement | Aucun appel API depuis domaines non autorisés |
| Validation inputs | Pydantic (FastAPI) | Aucune donnée malformée n'atteint la DB |
| Injection prompts | Sanitisation avant Claude API | Aucune instruction malveillante dans les prompts |
| Secrets | Variables d'environnement uniquement | Aucune clé dans le code ou GitHub |
| Audit logging | Chaque accès loggé | Traçabilité complète des actions |
| Headers sécurité | X-Content-Type, X-Frame, CSP | Protection navigateur standard |

### Principe de minimisation des données
Nous collectons uniquement ce que le diagnostic nécessite.
Aucune donnée personnelle superflue n'est demandée ni stockée.
Conforme aux bonnes pratiques RGPD.

### En cas de score Green élevé ou données financières sensibles
Les champs critiques (projections financières, données bancaires
éventuelles) sont chiffrés au niveau du champ avant stockage —
pas seulement au niveau de la base de données.

### Transparence
L'entrepreneur sait exactement quelles données sont collectées,
pourquoi, et comment elles sont protégées.
Aucune revente, aucune utilisation publicitaire.

Les documents uploadés sont chiffrés au repos, scopés à l'utilisateur
authentifié, et peuvent être supprimés sur demande après analyse.


### Bonus — Assistant Vocal Trilingue
Assistant conversationnel en Français, Arabe et Darija Tunisienne,
ancré dans les outputs du diagnostic et de la base de connaissances.

---

##  Architecture

[React Dashboard]

│

├──► Questionnaire adaptatif

│

└──► Upload documents optionnel (PDF · JPG · PNG)

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

Trilingual FR/AR

│

├──► Dashboard React · Mon Parcours

│

└──► PDF Report Generator · ReportLab · Rapport téléchargeable

# description de l'architecture 
React Frontend — single SPA in French/Arabic, calls the gateway with REST, renders the dashboard, Mon Parcours view, and scores.
FastAPI Gateway — single entry point, routes /diagnose, /score, /roadmap to the right microservice, handles auth.
3 Microservices — each is its own FastAPI app (can run as separate containers):

MS1: Diagnostic — LLM-driven adaptive questionnaire + rule-based maturity classifier
MS2: Scoring — weighted formula engine for the 5 scores + LLM for natural-language justification
MS3: RAG — pgvector retrieval over the knowledge base + roadmap generation

PostgreSQL (shared DB) — the project_profiles table is your shared state JSON: every microservice reads from it and writes to it, so they stay aware of each other's outputs without direct coupling. This is the key design decision to highlight in your README.
Cross-module triggers — the arrows between microservices show the integration: a diagnostic gap triggers MS3 retrieval, a low sub-score triggers MS3 roadmap action, MS3 can query MS1 for missing profile fields.
---

## 🛠️ Stack Technique

| Couche | Technologie |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | React + Tailwind CSS |
| LLM | Claude API (Anthropic) — claude-sonnet-4-6 |
| Vision / Documents | Claude Vision API — PDF, JPG, PNG |
| Génération PDF | ReportLab |
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
```

```env
# .env — variables requises
ANTHROPIC_API_KEY=your_key_here
MAX_UPLOAD_SIZE_MB=10
ALLOWED_FILE_TYPES=pdf,jpg,jpeg,png
```

```bash
# Frontend
cd frontend
npm install
npm start
```

---



## Protocole d'Évaluation

| Métrique | Description | Cible |
|---|---|---|
| Classification accuracy | 30 profils labellisés (5 par stade) | — |
| Precision@3 | Pertinence des ressources récupérées sur 10 profils | — |
| Document extraction accuracy | Signaux extraits vs signaux réels sur 10 documents | >= 75% |

Résultats dans `/data/evaluation/`

---

##  Langues Supportées

| Langue | Rapport PDF |
|---|---|
| 🇫🇷 Français | Oui |
| 🇸🇦 Arabe MSA | Oui |
| 🇹🇳 Darija Tunisienne | Oui |

---

*Massar — مسار | AINS Hackathon 2026 — Tunisie*
