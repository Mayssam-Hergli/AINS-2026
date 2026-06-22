const DIMENSION_LABELS = {
  market: 'Marché',
  commercial: 'Commercial',
  innovation: 'Innovation',
  scalability: 'Scalabilité',
  green: 'Impact Environnemental',
}

const SUB_LABELS = {
  taille_marche: 'Taille du marché',
  validation_client: 'Validation client',
  modele_revenus: 'Modèle de revenus',
  proposition_valeur: 'Proposition de valeur',
  maturite_produit: 'Maturité produit',
  strategie_pricing: 'Stratégie de pricing',
  alignement_besoin: 'Alignement besoin',
  nouveaute_locale: 'Nouveauté locale',
  intensite_technologique: 'Intensité technologique',
  barriere_entree: 'Barrière à l\'entrée',
  replicabilite: 'Réplicabilité',
  dependance_manuelle: 'Dépendance manuelle',
  potentiel_geographique: 'Potentiel géographique',
  climat_air: 'Climat & Air',
  eau: 'Eau',
  sols_biodiversite: 'Sols & Biodiversité',
  ressources_dechets: 'Ressources & Déchets',
}

const UNDP_COLORS = {
  'Très faible impact': 'bg-green-100 text-green-800',
  'Faible impact': 'bg-lime-100 text-lime-800',
  'Impact modéré': 'bg-yellow-100 text-yellow-800',
  'Impact élevé': 'bg-orange-100 text-orange-800',
  'Impact très élevé': 'bg-red-100 text-red-800',
}

function scoreColor(v) {
  if (v === null || v === undefined) return 'text-gray-400'
  if (v >= 70) return 'text-green-600'
  if (v >= 50) return 'text-yellow-600'
  return 'text-red-600'
}

function barColor(v) {
  if (v === null || v === undefined) return 'bg-gray-200'
  if (v >= 70) return 'bg-green-500'
  if (v >= 50) return 'bg-yellow-400'
  return 'bg-red-500'
}

function ScoreBar({ value, label }) {
  const pct = Math.min(100, Math.max(0, value ?? 0))
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className={`font-medium ${scoreColor(value)}`}>
          {value !== null && value !== undefined ? `${value}/100` : 'N/A'}
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function ScoreCard({ dimension, data }) {
  if (!data) return null

  const isGreen = dimension === 'green'
  const composite = data.composite
  const subItems = isGreen ? data.pillars : data.sub_scores

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-800">{DIMENSION_LABELS[dimension] || dimension}</h3>
          {isGreen && data.undp_classification && (
            <span className={`mt-1 inline-block text-xs font-medium px-2 py-0.5 rounded-full ${UNDP_COLORS[data.undp_classification] || 'bg-gray-100 text-gray-700'}`}>
              {data.undp_classification}
            </span>
          )}
        </div>
        <div className="text-right">
          <span className={`text-3xl font-bold ${scoreColor(composite)}`}>
            {composite !== null && composite !== undefined ? Math.round(composite) : '—'}
          </span>
          <span className="text-gray-400 text-sm ml-0.5">/100</span>
        </div>
      </div>

      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${barColor(composite)}`}
          style={{ width: `${Math.min(100, composite ?? 0)}%` }}
        />
      </div>

      {subItems && Object.entries(subItems).length > 0 && (
        <div className="pt-2 space-y-3 border-t border-gray-50">
          {Object.entries(subItems).map(([key, sub]) => {
            const value = isGreen
              ? Math.round((1 - (sub.score - 1) / 4) * 100)
              : sub.value
            return (
              <ScoreBar
                key={key}
                label={SUB_LABELS[key] || key}
                value={value}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
