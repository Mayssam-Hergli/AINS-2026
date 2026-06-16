# Méthodologie de Scoring — AINS 2026

## Vue d'ensemble

Cinq scores composites évaluent chaque projet entrepreneurial de 
manière indépendante. Chaque score se décompose en sous-critères 
pondérés avec des poids explicites et documentés.

Les scores sont calculés à partir des réponses collectées pendant 
le diagnostic adaptatif. Aucun questionnaire supplémentaire n'est 
requis sauf pour les questions spécifiques au Green Score.

Chaque score est accompagné d'une justification en langage naturel 
générée par Claude API, ancrée dans les données collectées — 
pas dans des connaissances générales.

---

## 1. Score Marché

### Problème mesuré
Un entrepreneur peut opérer sur un grand marché mais sans demande 
validée. Ce score distingue le potentiel théorique de la traction réelle.

### Sous-critères et Pondérations

| Critère | Poids | Mesure |
|---|---|---|
| Taille du marché adressable | 30% | Données sectorielles + marché cible déclaré |
| Preuves de validation client | 40% | Interviews, LOI, contrats pilotes, revenus |
| Clarté du modèle de revenus | 30% | Modèle documenté + viabilité |

### Logique d'Agrégation
Moyenne pondérée. La validation client est pondérée le plus fort 
car sans demande validée, la taille du marché reste théorique.

### Détection d'Anomalies
🚩 Grande taille de marché déclarée + zéro preuve de validation client
🚩 Modèle de revenus détaillé + aucun client identifié

---

## 2. Score Offre Commerciale

### Problème mesuré
Un produit peut être techniquement avancé mais mal positionné, 
mal pricé, ou mal aligné avec le besoin réel du client.

### Sous-critères et Pondérations

| Critère | Poids | Mesure |
|---|---|---|
| Clarté de la proposition de valeur | 30% | Différenciation clairement articulée |
| Maturité du produit/service | 25% | Stade de développement (idée → MVP → produit) |
| Cohérence de la stratégie de prix | 25% | Modèle de pricing défini et justifié |
| Alignement offre-besoin | 20% | Correspondance entre offre et besoin validé |

### Détection d'Anomalies
🚩 Haute maturité produit + aucun besoin client validé
🚩 Prix détaillé + aucune étude de marché conduite

---

## 3. Score Innovation

### Problème mesuré
L'innovation n'est pas absolue — elle est relative au marché local.
Un projet peut être innovant en Tunisie sans être nouveau globalement.

### Sous-critères et Pondérations

| Critère | Poids | Mesure |
|---|---|---|
| Nouveauté locale (marché tunisien) | 35% | Différenciation vs offres existantes en Tunisie |
| Intensité technologique | 30% | Composante tech de la solution |
| Barrière à l'entrée | 35% | PI, effets réseau, coûts de changement |

### Détection d'Anomalies
🚩 Haute innovation déclarée + solution identique à un concurrent local existant
🚩 Haute barrière à l'entrée + aucune PI ni avantage défendable documenté

---

## 4. Score Scalabilité

### Problème mesuré
Beaucoup de projets tunisiens sont viables localement mais 
structurellement non-scalables — dépendants d'un accompagnement 
manuel qui ne peut pas croître linéairement.

### Sous-critères et Pondérations

| Critère | Poids | Mesure |
|---|---|---|
| Réplicabilité sans coût linéaire | 35% | Croissance possible sans coût proportionnel |
| Dépendance à l'accompagnement manuel | 30% | Niveau d'intervention humaine requis |
| Potentiel géographique | 35% | Marché adressable au-delà du marché initial |

### Détection d'Anomalies
🚩 Haute scalabilité déclarée + forte dépendance à l'accompagnement manuel
🚩 Expansion géographique planifiée + modèle entièrement dépendant du contexte local

---

## 5. Green Score (Référentiel PNUD)

### Source du Référentiel
Les sous-critères et la classification globale sont dérivés du 
cadre d'évaluation environnementale présenté par le PNUD Tunisie 
lors du workshop AINS Hackathon 2026.

### Les Quatre Piliers

| Pilier | Poids | Critères d'évaluation |
|---|---|---|
| 🌍 Climat / Air | 35% | Consommation d'énergie, type d'énergie, émissions transport |
| 💧 Eau | 25% | Volume utilisé, origine, rejets, traitement |
| 🌱 Sols et Biodiversité | 20% | Type de zone, surface impactée, perturbation écosystèmes |
| ♻️ Ressources et Déchets | 20% | Matières utilisées, volume déchets, recyclage |

### Échelle de Notation PNUD
Chaque pilier noté de 1 à 5 :
- 1 = impact très faible (meilleur)
- 5 = impact très élevé (pire)

### Calcul
Score brut total = somme des 4 piliers (4 à 20)

Score affiché (0-100) = 100 - ((score_brut - 4) / 16 × 100)

### Table de Classification PNUD

| Score Brut | Niveau d'Impact Environnemental |
|---|---|
| 4 – 7 | Très faible impact ✅ |
| 8 – 11 | Faible impact 🟡 |
| 12 – 15 | Impact modéré 🟠 |
| 16 – 18 | Impact élevé 🔴 |
| 19 – 20 | Impact très élevé 🚨 |

### Exemples Validés PNUD (Workshop AINS 2026)

| Projet | Climat | Eau | Sols | Ressources | Total | Classification |
|---|---|---|---|---|---|---|
| Atelier tissage artisanal (Kilim) | 2 | 2 | 1 | 2 | **7** | Très faible impact |
| Unité briques en ciment | 4 | 3 | 4 | 4 | **15** | Impact modéré |

### Fonctionnalité Green Optimization
Pour chaque pilier scoring ≥ 3, la plateforme génère une 
recommandation de substitution avec estimation de coût basée 
sur des données tunisiennes réelles :

- **Énergie** : Alternative solaire + calcul subvention ANME 
  (jusqu'à 30%) + programme net metering STEG
- **Eau** : Systèmes de recyclage + conformité ONAS
- **Déchets** : Partenaires ANGed certifiés + économie circulaire

### Blocage Financement Vert
Un score brut ≥ 16 (Impact élevé) est automatiquement signalé 
comme bloqueur dans le diagnostic et déclenche des actions 
prioritaires dans la roadmap.

---

## Logique d'Agrégation Globale

Les 5 scores sont indépendants et ne sont pas moyennés entre eux.
Un score faible sur une dimension fondamentale n'est pas masqué 
par des scores forts ailleurs.

Le moteur de diagnostic utilise les profils de scores pour :
- Identifier le gap à plus fort levier par dimension
- Déclencher la récupération KB pertinente pour les scores faibles
- Générer des actions prioritaires dans la roadmap personnalisée

---

## Protocole d'Évaluation

| Métrique | Description | Cible |
|---|---|---|
| Classification accuracy | % de profils correctement classifiés par stade | ≥ 80% |
| Precision@3 | % de ressources pertinentes dans le top 3 récupéré | ≥ 70% |

Test set : 30 profils labellisés (5 par stade) dans `/data/evaluation/`
Résultats complets dans `/data/evaluation/evaluation_report.md`
