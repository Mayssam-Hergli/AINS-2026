MS2 — Moteur de Scoring · Documentation technique


Module appartenant à Person 1. Calcule 5 scores composites explicables
à partir des réponses du diagnostic (MS1), détecte les anomalies
inter-dimensionnelles, et génère des justifications en langage naturel.

Tous les scores sont déterministes. L'agent IA orchestre et explique —
il ne calcule jamais. Chaque nombre est traçable jusqu'à une formule.




1. Principe général

Chaque score composite est sur 100. Il se décompose en sous-critères,
chacun ayant :


une valeur (0 à 100) obtenue en mappant une réponse catégorielle
vers un nombre via une table de correspondance
un poids (la somme des poids d'un score = 1.0)


La formule générale d'un score composite est :

composite = round( Σ (valeur_sous_critère × poids_sous_critère), 1 )

Les poids ne sont pas arbitraires : ils reflètent l'importance réelle
de chaque critère dans le domaine. Un critère fondamental (ex : la
validation client) pèse plus lourd pour qu'une faiblesse critique ne
soit jamais masquée par une force ailleurs.


2. Score Marché (market.py)

Mesure la solidité de l'opportunité de marché.

Sous-critèrePoidsChamp sourceMappingTaille marché30%market_sizesmall=25 · medium=50 · large=75 · very_large=100Validation client40%(3 champs combinés, voir ci-dessous)0 à 100Modèle de revenus30%revenue_model_documented + revenue_model_typevoir ci-dessous

Validation client (40% — le poids le plus élevé du module, par design)

Combinaison de 3 signaux, additionnés (max 100) :


Entretiens clients (customer_interviews) : "0"→0 · "1-5"→15 · "6-10"→25 · "10+"→40
LOI signées (has_loi) : 0→0 · 1→15 · 2 ou plus→30
Clients payants (has_paying_customers) : false→0 · true→30


Modèle de revenus (30%)


documenté ET type défini → 100
documenté MAIS type "undefined" → 60
brouillon (draft) → 40
aucun (none) → 10


Formule :

composite = round(taille×0.30 + validation×0.40 + revenus×0.30, 1)

Pourquoi validation pèse 40% : un grand marché ne vaut rien si
personne n'a confirmé vouloir acheter. Le poids fort empêche un score
de taille élevé de masquer l'absence de preuve de demande.


3. Score Offre Commerciale (commercial.py)

Mesure la solidité de l'offre elle-même.

Sous-critèrePoidsChamp sourceMappingProposition de valeur30%value_proposition_claritynone=10 · vague=40 · clear=70 · differentiated=100Maturité produit25%product_maturityidea=15 · prototype=45 · mvp=70 · product=100Stratégie pricing25%pricing_strategynone=10 · draft=50 · defined=100Alignement offre-besoin20%offer_need_alignmentnone=10 · partial=50 · validated=100

Formule :

composite = round(prop_valeur×0.30 + maturité×0.25 + pricing×0.25 + alignement×0.20, 1)


4. Score Innovation (innovation.py)

Mesure l'originalité et la défensibilité du projet.

Sous-critèrePoidsChamp sourceMappingNouveauté locale35%local_noveltyexisting=10 · similar=40 · new=70 · unique=100Intensité technologique30%technology_intensitynone=10 · low=40 · medium=70 · high=100Barrière à l'entrée35%barrier_to_entry (+ bonus IP)none=10 · low=40 · medium=70 · high=100

Bonus propriété intellectuelle appliqué à la barrière à l'entrée :


has_ip_protection = "granted" → +15 points
has_ip_protection = "pending" → +5 points
has_ip_protection = "none" → aucun bonus
Plafonné à 100 (la barrière ne dépasse jamais 100, même avec bonus)


Formule :

barrière = min(barrière_base + bonus_IP, 100)
composite = round(nouveauté×0.35 + intensité×0.30 + barrière×0.35, 1)


5. Score Scalabilité (scalability.py)

Mesure la capacité à croître sans explosion des coûts.

Sous-critèrePoidsChamp sourceMappingRéplicabilité35%replicabilitymanual=20 · semi_auto=60 · automated=100Dépendance manuelle30%manual_dependencyinversé : high=10 · medium=40 · low=70 · none=100Potentiel géographique35%geographic_potentiallocal=25 · national=50 · regional=75 · global=100

Formule :

composite = round(réplicabilité×0.35 + dépendance×0.30 + géo×0.35, 1)

Pourquoi la dépendance manuelle est inversée : moins le projet
dépend d'un accompagnement manuel, mieux il scale. Donc "aucune
dépendance" = 100, "forte dépendance" = 10.

Note importante : ce score à lui seul ne peut PAS détecter la
contradiction "scalabilité élevée + forte dépendance manuelle", car
la dépendance ne pèse que 30%. Un projet automatisé et mondial reste
à 73 malgré une dépendance manuelle au pire niveau. C'est exactement
pourquoi la détection d'anomalies (section 7) est nécessaire et
centralisée.


6. Green Score (green.py) — Référentiel PNUD

Mesure l'impact environnemental selon le référentiel PNUD présenté
au workshop AINS 2026. Logique différente des 4 autres scores.

4 piliers, chacun noté de 1 à 5 (1 = meilleur / impact le plus
faible, 5 = pire / impact le plus élevé). Chaque pilier est la moyenne
de 3 champs.

PilierPoidsChamps (3 par pilier)Climat / Air35%energy_source · energy_consumption · transport_activityEau25%water_volume · water_origin · wastewater_treatmentSols et Biodiversité20%zone_type · surface_impacted · ecosystem_disruptionRessources et Déchets20%raw_material_consumption · waste_volume · recycling_strategy

Chaque champ est mappé sur une échelle 1-5 (1=meilleur, 5=pire).
Le score d'un pilier = moyenne de ses 3 champs.

Calcul du total brut et du score affiché :

undp_raw_total = somme des 4 scores de piliers     (plage : 4 à 20)
score_affiché  = round(100 - ((undp_raw_total - 4) / 16 × 100), 1)

Le score affiché inverse l'échelle : un faible impact brut (proche de 4)
donne un score affiché élevé (proche de 100), car un faible impact
environnemental est une bonne chose.

Classification PNUD (sur le total brut 4-20) :

Total brutClassification4 – 7Très faible impact8 – 11Faible impact12 – 15Impact modéré16 – 18Impact élevé19 – 20Impact très élevé

Validation : la formule a été testée contre les 2 exemples validés
par le PNUD au workshop :


Atelier tissage Kilim : piliers 2/2/1/2 → total 7 → "Très faible impact" → 81.2
Unité briques ciment : piliers 4/3/4/4 → total 15 → "Impact modéré" → 31.2


Les deux correspondent exactement.


7. Détection d'anomalies (anomaly.py)

Centralisée : tourne UNE SEULE FOIS, après que les 5 scores existent,
avec visibilité complète sur toutes les dimensions. Les fonctions de
scoring individuelles ne contiennent AUCUNE logique d'anomalie — elles
retournent uniquement des nombres.

detect_all_anomalies(diagnostic_answers, all_scores) lit les réponses
brutes ET les scores calculés pour détecter des contradictions qu'aucun
score seul ne peut voir.

CodeSévéritéDéclencheurmarket_no_validationhautemarché large/very_large + 0 entretien + aucun client payantrevenue_no_clientshautemodèle de revenus documenté + aucun client payant + aucune LOIscalability_manual_conflictmoyennescalabilité élevée (automated/global/regional) + forte dépendance manuelle (high/medium)green_fundraising_riskmoyenneundp_raw_total ≥ 16 + pitch deck + financement recherchéproduct_built_unvalidatedmoyenneproduct_maturity = "product" + offer_need_alignment = "none"

Note technique importante : les valeurs catégorielles brutes
(ex : offer_need_alignment) vivent dans diagnostic_answers sous
forme de chaînes. Les objets de score dans all_scores ne contiennent
que des valeurs numériques — pas les chaînes d'origine. Toute vérification
d'anomalie ayant besoin de la catégorie brute doit la lire depuis
diagnostic_answers, jamais la reconstituer depuis all_scores.


8. Agrégateur déterministe (engine.py)

compute_all_scores(diagnostic_answers) exécute les 5 fonctions de
scoring + la détection d'anomalies, et retourne un payload unifié :

json{
  "scores": {
    "market": {...}, "commercial": {...}, "innovation": {...},
    "scalability": {...}, "green": {...}
  },
  "anomaly_flags": [...],
  "low_scoring_dimensions": [...],
  "green_pillars_flagged": [...]
}


low_scoring_dimensions : toute dimension dont le composite est
strictement < 50. Les scores None (échec de calcul) sont exclus —
une dimension non calculée est "inconnue", pas "faible".
green_pillars_flagged : tout pilier Green avec un score ≥ 3.


Ces deux champs sont lus par MS3 pour décider quelles ressources
récupérer.

Isolation des erreurs : chaque appel de fonction de scoring est
encapsulé indépendamment. Si un champ manque, cette dimension retourne
{"composite": None, "error": ...} pendant que les 4 autres se calculent
normalement. Le moteur ne plante jamais sur des données incomplètes —
il fait remonter l'incertitude au lieu de la cacher.

engine.py est la vérité de référence déterministe : il sert à
vérifier que l'agent produit des nombres identiques.


9. La couche agent (agent.py + tools.py + system_prompt.py + llm_client.py)

L'agent est un LLM (Llama via Groq en test, Claude en production) dont
le rôle est d'orchestrer et d'expliquer — JAMAIS de calculer.

Déroulé d'une session de scoring :


L'agent reçoit les diagnostic_answers
Il appelle les 5 outils de scoring dans l'ordre fixe
(market → commercial → innovation → scalability → green)
Chaque outil exécute la VRAIE fonction Python déterministe et
retourne le vrai nombre
Une fois les 5 scores obtenus, l'agent appelle detect_all_anomalies
L'agent rédige alors UNIQUEMENT les justifications en français à
partir des vrais nombres
Le payload final fusionne les nombres déterministes (des outils)
avec les justifications (de l'agent)


Garde-fous (double application) :


Le system prompt interdit à l'agent d'inventer un nombre ou de sauter
un outil
Le code dans agent.py REND IMPOSSIBLE l'appel de detect_all_anomalies
avant que les 5 scores existent — l'agent est rejeté et doit appeler
les outils manquants d'abord


Source unique de vérité : les nombres viennent TOUJOURS des outils,
jamais du texte de l'agent. L'agent ne fait qu'ajouter la couche
langage. Cela évite que l'agent dise 43 alors que l'outil a calculé 42.

llm_client.py isole le fournisseur LLM : changer de Groq à Claude
se fait via une variable d'environnement (LLM_PROVIDER), sans toucher
au reste du code. Une seule différence à gérer : le format des appels
d'outils diffère entre Groq (format OpenAI) et Claude (format Anthropic),
normalisé dans ce seul fichier.


10. Exemple complet — profil "fondateur surconfiant"

Profil test : grand marché déclaré mais aucune validation, produit
construit mais jamais validé, scalable mais forte dépendance manuelle.

ScoreCompositeLectureMarché42.0grand marché (100×0.30) mais validation nulle (0×0.40) + revenus brouillon (40×0.30)Offre Commerciale82.0offre forte mais alignement besoin faible (10×0.20)Innovation100.0unique + tech élevée + barrière élevéeScalabilité73.0automatisé + mondial, mais dépendance manuelle au pire (10×0.30)Green50.0impact modéré, total brut 12/20

3 anomalies déclenchées :


market_no_validation (haute)
scalability_manual_conflict (moyenne)
product_built_unvalidated (moyenne)


Ce profil illustre la valeur centrale du module : sur les scores
individuels il a l'air correct (42, 82, 100, 73, 50), mais la couche
d'anomalie révèle que c'est un fondateur surconfiant qui a construit
avant de valider — exactement l'écart perception-réalité que le cahier
des charges récompense.

Preuve d'auditabilité (Test 1) : l'agent live produit EXACTEMENT
ces mêmes nombres que engine.py. L'IA n'invente aucun chiffre —
elle orchestre et explique, le calcul reste déterministe.


11. État du module

ComposantStatutTestsgreen.pyFaitvalidé contre 2 exemples PNUDmarket.pyFait3commercial.pyFait3innovation.pyFait5scalability.pyFait4anomaly.pyFait16 (5 checks)engine.pyFait3tools.pyFait7system_prompt.pyFait12 checks couvertureagent.pyFait3 (live Groq, scores == engine.py)api/scoring.pyEn cours—

Total : 44 tests déterministes + 3 tests agent live, tous passent.


12. Dépendance ouverte à confirmer avec MS1

Les noms exacts des champs dans diagnostic_answers (écrits par MS1)
doivent correspondre à ce que les fonctions de scoring attendent :
market_size, customer_interviews, has_loi, has_paying_customers,
revenue_model_documented, revenue_model_type,
value_proposition_clarity, product_maturity, pricing_strategy,
offer_need_alignment, local_novelty, technology_intensity,
barrier_to_entry, has_ip_protection, replicability,
manual_dependency, geographic_potential, plus les 12 champs Green
(energy_source, energy_consumption, transport_activity, water_volume,
water_origin, wastewater_treatment, zone_type, surface_impacted,
ecosystem_disruption, raw_material_consumption, waste_volume,
recycling_strategy).

Si MS1 utilise des noms différents (ex : secteur vs sector), chaque
score casse à l'intégration. À confirmer avant de brancher api/scoring.py.