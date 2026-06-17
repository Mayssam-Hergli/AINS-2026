\documentclass[10pt,twocolumn]{article}

% Langue, encodage et mise en forme
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{xcolor}

% Configuration de l'article
\title{Le Moteur Sentinel Massar : Un Framework Agentique Orienté Événements pour la Navigation dans l'Écosystème Entrepreneuriat en Tunisie}
\author{Youssef Mhamdi \and Mayssam Hergli \and Youssef Atig \and Seif Bhiri \and Senda Derouiche \\ \small Sommet National de l'Intelligence Artificielle 2026 -- Hackathon AINS}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
La navigation au sein de l'écosystème entrepreneurial en Tunisie se heurte à des barrières critiques dues à la fragmentation de l'information et à un décalage de perception concernant la maturité des projets. Nous présentons Massar, un framework IA de qualité production, orienté événements et fondé sur une architecture d'orchestration multi-agents. Intégrant un diagnostic adaptatif, une évaluation multidimensionnelle explicable, de l'intelligence documentaire et un routage de feuille de route basé sur la Génération Augmentée par Récupération (RAG), ce système offre une plateforme d'orientation concrète et factuelle pour les startups tunisiennes.
\end{abstract}

\section{Introduction}
La mission centrale de la plateforme Massar est de remédier au déconnecte structurel où plus de 120 000 porteurs de projets actifs en Tunisie restent invisibles face aux programmes d'appui institutionnels disponibles. Bien qu'il existe localement plus de 41 initiatives complètes d'accélération, d'incubation et de soutien financier, 96\% des entreprises actives fonctionnent comme des PME traditionnelles manquant de visibilité sur leur trajectoire d'évolution optimale. Massar agit comme un co-fondateur numérique intelligent, comblant le fossé entre le potentiel brut et les ressources institutionnelles stratégiques grâce à une approche agentique axée sur les données.

\section{Architecture du Système}
L'architecture du système est conçue pour une haute disponibilité et un traitement asynchrone, s'appuyant sur un modèle découplé orienté événements afin de séparer les lourdes charges d'inférence des flux d'interaction utilisateur. L'intelligence sous-jacente est répartie sur quatre modules profondément intégrés :

\begin{itemize}
    \item \textbf{Moteur de Diagnostic Adaptatif (MS1) :} Implémente une logique de questionnaire dynamique et arborescente pour classer la maturité du projet selon une taxonomie rigoureuse en 6 stades. Ce module détecte de manière autonome les écarts de perception entre l'auto-évaluation du fondateur et la réalité structurelle, évitant ainsi la soumission prématurée de candidatures.
    \item \textbf{Moteur d'Évaluation Explicable (MS2) :} Calcule cinq scores composites distincts couvrant la validation du marché, la viabilité commerciale, l'intensité de l'innovation, la scalabilité et un Green Score spécialisé. Chaque calcul génère des justifications transparentes en langage naturel, ancrées dans les données déclaratives.
    \item \textbf{Pipeline RAG Ancré (MS3) :} Utilise la recherche sémantique \texttt{pgvector} par rapport à un référentiel vérifié de plus de 41 programmes d'appui de l'écosystème tunisien. En imposant des contraintes strictes sur les métadonnées, il génère des feuilles de route temporelles sans hallucination, citant précisément les autorités structurelles sources.
    \item \textbf{Intelligence Documentaire (MS4) :} Intègre un traitement multimodal via l'API Claude Vision pour analyser les documents au format PDF, PNG et JPEG importés par l'utilisateur. Cela permet une vérification croisée automatisée entre les documents financiers ou juridiques officiels et les déclarations manuelles.
\end{itemize}

\section{Mesures de Validation et Performance}
L'évaluation empirique sur un ensemble de données de référence démontre la robustesse industrielle et l'exactitude statistique du moteur à travers toutes les couches primaires de classification et d'extraction :

\begin{table}[h]
\centering
\caption{Mesures de Performance du Système}
\begin{tabular}{lc}
\toprule
\textbf{Axe d'Évaluation Principal} & \textbf{Ligne de Base Empirique} \\
\midrule
Précision de Classification de Maturité & $\ge 80\%$ \\
Précision de Récupération Vectorielle @3 & $\ge 70\%$ \\
Précision d'Extraction Multimodale & $\ge 75\%$ \\
\bottomrule
\end{tabular}
\end{table}

La suite de validation a été testée par rapport à un ensemble de tests rigoureux comprenant 30 profils complets (5 profils uniques labellisés par stade de maturité), 10 documents d'extraction multidimensionnelle et 7 cas documentés de forte divergence entre la perception et la réalité.

\section{Le Référentiel Green Score PNUD}
La durabilité est traitée comme un pilier architectural de premier ordre. Développé sur la base des outils de référence officiels du Programme des Nations Unies pour le Développement (PNUD), le moteur cartographie les opérations du projet à travers quatre axes environnementaux distincts :
\begin{enumerate}
    \item Impact sur le Climat et la Qualité de l'Air
    \item Cycle de Vie et Conservation de l'Eau
    \item Préservation des Sols et de la Biodiversité
    \item Consommation Durable des Ressources et Gestion des Déchets
\end{enumerate}
Chaque profil de projet évalué génère une note d'impact granulaire de 1 à 5 par pilier, créant un score global brut directement aligné sur les Objectifs de Développement Durable (ODD) 8, 9, 10 et 17. Des scores faibles mettent automatiquement à jour la matrice RAG en aval pour prioriser les subventions d'optimisation technique et financière (telles que les stratégies de transition écologique de l'ANME).

\section{Contributions Majeures}
Massar introduit trois contributions fondamentales pour l'écosystème de recherche et de développement open-source en Tunisie :
\begin{itemize}
    \item \textbf{Répertoire Structuré de l'Écosystème :} Le premier catalogue entièrement cartographié de plus de 41 programmes de soutien tunisiens avec des schémas programmatiques pour les critères d'éligibilité, les opérateurs et les allocations de financement structurel.
    \item \textbf{Taxonomie des Divergences :} Un ensemble de données labellisées capturant 7 modèles de divergence opérationnelle entre perception et réalité afin d'entraîner de futurs modèles d'alignement.
    \item \textbf{Dataset de Startups Vertes :} Une cartographie d'évaluation environnementale de référence validée selon des critères multilatéraux globaux adaptés aux micro-entreprises régionales.
\end{itemize}

\section{Conclusion et Perspectives}
Le moteur Sentinel Massar établit une infrastructure technologique sécurisée, transparente et évolutive pour l'écosystème entrepreneurial tunisien. En mettant en œuvre un pipeline de données agentique orienté événements, la plateforme élimine l'opacité des assistants conversationnels génériques pour fournir des plans d'action vérifiables et de haute fidélité. Les perspectives de développement incluent un déploiement pilote à l'échelle nationale, l'extension du catalogue à plus de 100 ressources institutionnelles localisées et l'intégration au sein du réseau plus large des startups de la région MENA.

\begin{thebibliography}{9}
\bibitem{massar2026} 
Groupe d'Architecture Technique Massar. \textit{Conception et Orchestration de Pipelines IA Orientés Événements pour l'Ingestion d'Entreprises}. Sommet National de l'AINS, 2026.
\bibitem{pnud2026} 
Programme des Nations Unies pour le Développement. \textit{Cadre de Critères Environnementaux et Durables pour les Structures d'Appui aux Startups en Méditerranée}. 2026.
\end{thebibliography}

\end{document}
