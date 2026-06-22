import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { profilesApi } from '../api/profiles'
import Spinner from '../components/Spinner'

// Demo profile: strong Tunisian EdTech startup
const DEMO_ANSWERS = {
  // Market
  market_size: 'large',
  customer_interviews: '10+',
  has_loi: 1,
  has_paying_customers: true,
  revenue_model_documented: 'documented',
  revenue_model_type: 'saas',
  // Commercial
  value_proposition_clarity: 'differentiated',
  product_maturity: 'mvp',
  pricing_strategy: 'defined',
  offer_need_alignment: 'validated',
  // Innovation
  local_novelty: 'new',
  technology_intensity: 'high',
  barrier_to_entry: 'high',
  has_ip_protection: 'pending',
  // Scalability
  replicability: 'automated',
  manual_dependency: 'low',
  geographic_potential: 'regional',
  has_pitch_deck: true,
  funding_needed: '500000',
  // Green
  energy_source: 'mixed_renewable_grid',
  energy_consumption: 'low',
  transport_activity: 'local',
  water_volume: 'low_controlled',
  water_origin: 'municipal_controlled',
  wastewater_treatment: 'full_treatment',
  zone_type: 'urban_industrial',
  surface_impacted: 'small',
  ecosystem_disruption: 'negligible',
  raw_material_consumption: 'low_recycled',
  waste_volume: 'low_managed',
  recycling_strategy: 'active_program',
}

const STEPS = [
  {
    title: 'Marché',
    fields: [
      { key: 'market_size', label: 'Taille de votre marché cible', type: 'select', options: [
        { value: 'small', label: 'Petit (< 1M TND)' },
        { value: 'medium', label: 'Moyen (1–10M TND)' },
        { value: 'large', label: 'Grand (10–100M TND)' },
        { value: 'very_large', label: 'Très grand (> 100M TND)' },
      ]},
      { key: 'customer_interviews', label: 'Entretiens clients réalisés', type: 'select', options: [
        { value: '0', label: 'Aucun' },
        { value: '1-5', label: '1 à 5' },
        { value: '6-10', label: '6 à 10' },
        { value: '10+', label: 'Plus de 10' },
      ]},
      { key: 'has_loi', label: 'Lettres d\'intention signées ?', type: 'select', options: [
        { value: 0, label: 'Non' },
        { value: 1, label: 'Oui' },
      ]},
      { key: 'has_paying_customers', label: 'Clients payants existants ?', type: 'select', options: [
        { value: false, label: 'Non' },
        { value: true, label: 'Oui' },
      ]},
      { key: 'revenue_model_documented', label: 'Modèle de revenus', type: 'select', options: [
        { value: 'none', label: 'Non défini' },
        { value: 'draft', label: 'En cours' },
        { value: 'documented', label: 'Documenté' },
      ]},
      { key: 'revenue_model_type', label: 'Type de modèle', type: 'select', options: [
        { value: 'undefined', label: 'Non défini' },
        { value: 'saas', label: 'SaaS / Abonnement' },
        { value: 'marketplace', label: 'Marketplace / Commission' },
        { value: 'freemium', label: 'Freemium' },
        { value: 'transactional', label: 'Transactionnel' },
      ]},
    ],
  },
  {
    title: 'Commercial',
    fields: [
      { key: 'value_proposition_clarity', label: 'Proposition de valeur', type: 'select', options: [
        { value: 'none', label: 'Inexistante' },
        { value: 'vague', label: 'Vague' },
        { value: 'clear', label: 'Claire' },
        { value: 'differentiated', label: 'Différenciée' },
      ]},
      { key: 'product_maturity', label: 'Maturité du produit', type: 'select', options: [
        { value: 'idea', label: 'Idée' },
        { value: 'prototype', label: 'Prototype' },
        { value: 'mvp', label: 'MVP' },
        { value: 'product', label: 'Produit fini' },
      ]},
      { key: 'pricing_strategy', label: 'Stratégie de pricing', type: 'select', options: [
        { value: 'none', label: 'Absente' },
        { value: 'draft', label: 'En cours de définition' },
        { value: 'defined', label: 'Définie' },
      ]},
      { key: 'offer_need_alignment', label: 'Adéquation offre-besoin', type: 'select', options: [
        { value: 'none', label: 'Non validée' },
        { value: 'partial', label: 'Partiellement validée' },
        { value: 'validated', label: 'Validée' },
      ]},
    ],
  },
  {
    title: 'Innovation',
    fields: [
      { key: 'local_novelty', label: 'Nouveauté sur le marché local', type: 'select', options: [
        { value: 'existing', label: 'Solution existante' },
        { value: 'similar', label: 'Similaire à l\'existant' },
        { value: 'new', label: 'Nouvelle approche' },
        { value: 'unique', label: 'Unique / Pionnier' },
      ]},
      { key: 'technology_intensity', label: 'Intensité technologique', type: 'select', options: [
        { value: 'none', label: 'Aucune' },
        { value: 'low', label: 'Faible' },
        { value: 'medium', label: 'Moyenne' },
        { value: 'high', label: 'Élevée' },
      ]},
      { key: 'barrier_to_entry', label: 'Barrière à l\'entrée', type: 'select', options: [
        { value: 'none', label: 'Nulle' },
        { value: 'low', label: 'Faible' },
        { value: 'medium', label: 'Moyenne' },
        { value: 'high', label: 'Élevée' },
      ]},
      { key: 'has_ip_protection', label: 'Protection intellectuelle', type: 'select', options: [
        { value: 'none', label: 'Aucune' },
        { value: 'pending', label: 'En cours de dépôt' },
        { value: 'granted', label: 'Accordée' },
      ]},
    ],
  },
  {
    title: 'Scalabilité',
    fields: [
      { key: 'replicability', label: 'Réplicabilité du modèle', type: 'select', options: [
        { value: 'manual', label: 'Manuelle' },
        { value: 'semi_auto', label: 'Semi-automatisée' },
        { value: 'automated', label: 'Automatisée' },
      ]},
      { key: 'manual_dependency', label: 'Dépendance à l\'humain', type: 'select', options: [
        { value: 'high', label: 'Élevée' },
        { value: 'medium', label: 'Moyenne' },
        { value: 'low', label: 'Faible' },
        { value: 'none', label: 'Nulle' },
      ]},
      { key: 'geographic_potential', label: 'Potentiel géographique', type: 'select', options: [
        { value: 'local', label: 'Local (ville)' },
        { value: 'national', label: 'National' },
        { value: 'regional', label: 'Régional (Afrique / MENA)' },
        { value: 'global', label: 'International' },
      ]},
      { key: 'has_pitch_deck', label: 'Pitch deck disponible ?', type: 'select', options: [
        { value: false, label: 'Non' },
        { value: true, label: 'Oui' },
      ]},
      { key: 'funding_needed', label: 'Montant recherché (TND, optionnel)', type: 'text', placeholder: 'ex. 500000' },
    ],
  },
  {
    title: 'Impact Environnemental',
    fields: [
      { key: 'energy_source', label: 'Source d\'énergie principale', type: 'select', options: [
        { value: 'solar_wind', label: 'Solaire / Éolien' },
        { value: 'mixed_renewable_grid', label: 'Mix renouvelable + réseau' },
        { value: 'grid_steg', label: 'Réseau STEG' },
        { value: 'grid_diesel', label: 'Réseau + groupes électrogènes' },
        { value: 'diesel_only', label: 'Diesel uniquement' },
      ]},
      { key: 'energy_consumption', label: 'Consommation énergétique', type: 'select', options: [
        { value: 'minimal', label: 'Minimale' },
        { value: 'low', label: 'Faible' },
        { value: 'moderate', label: 'Modérée' },
        { value: 'high', label: 'Élevée' },
        { value: 'very_high', label: 'Très élevée' },
      ]},
      { key: 'transport_activity', label: 'Activité transport / logistique', type: 'select', options: [
        { value: 'none', label: 'Aucune' },
        { value: 'local', label: 'Locale (< 50 km)' },
        { value: 'regional', label: 'Régionale' },
        { value: 'national', label: 'Nationale' },
        { value: 'international', label: 'Internationale' },
      ]},
      { key: 'water_volume', label: 'Volume d\'eau utilisée', type: 'select', options: [
        { value: 'none', label: 'Aucune' },
        { value: 'low_controlled', label: 'Faible et contrôlée' },
        { value: 'moderate', label: 'Modérée' },
        { value: 'high', label: 'Élevée' },
        { value: 'very_high', label: 'Très élevée' },
      ]},
      { key: 'water_origin', label: 'Origine de l\'eau', type: 'select', options: [
        { value: 'rainwater_recycled', label: 'Pluie / Eau recyclée' },
        { value: 'municipal_controlled', label: 'Réseau municipal contrôlé' },
        { value: 'municipal_uncontrolled', label: 'Réseau municipal non contrôlé' },
        { value: 'groundwater', label: 'Nappe phréatique' },
        { value: 'natural_body', label: 'Cours d\'eau naturel' },
      ]},
      { key: 'wastewater_treatment', label: 'Traitement des eaux usées', type: 'select', options: [
        { value: 'none_generated', label: 'Aucune eau usée générée' },
        { value: 'full_treatment', label: 'Traitement complet' },
        { value: 'partial_treatment', label: 'Traitement partiel' },
        { value: 'discharged_untreated', label: 'Rejet sans traitement' },
        { value: 'discharged_environment', label: 'Rejet en milieu naturel' },
      ]},
      { key: 'zone_type', label: 'Zone d\'activité', type: 'select', options: [
        { value: 'urban_industrial', label: 'Zone industrielle urbaine' },
        { value: 'suburban', label: 'Périurbaine' },
        { value: 'rural_agricultural', label: 'Zone rurale / agricole' },
        { value: 'near_protected', label: 'Proche d\'une zone protégée' },
        { value: 'inside_protected', label: 'Dans une zone protégée' },
      ]},
      { key: 'surface_impacted', label: 'Surface impactée', type: 'select', options: [
        { value: 'none', label: 'Nulle' },
        { value: 'small', label: 'Petite (< 500 m²)' },
        { value: 'medium', label: 'Moyenne' },
        { value: 'large', label: 'Grande' },
        { value: 'very_large', label: 'Très grande' },
      ]},
      { key: 'ecosystem_disruption', label: 'Impact sur les écosystèmes', type: 'select', options: [
        { value: 'none', label: 'Nul' },
        { value: 'negligible', label: 'Négligeable' },
        { value: 'moderate_reversible', label: 'Modéré et réversible' },
        { value: 'significant', label: 'Significatif' },
        { value: 'irreversible', label: 'Irréversible' },
      ]},
      { key: 'raw_material_consumption', label: 'Consommation de matières premières', type: 'select', options: [
        { value: 'none_minimal', label: 'Nulle / Minimale' },
        { value: 'low_recycled', label: 'Faible avec recyclage' },
        { value: 'moderate_partial', label: 'Modérée avec recyclage partiel' },
        { value: 'high_virgin', label: 'Élevée, matière vierge' },
        { value: 'very_high_no_recycling', label: 'Très élevée, aucun recyclage' },
      ]},
      { key: 'waste_volume', label: 'Volume de déchets produits', type: 'select', options: [
        { value: 'none', label: 'Nul' },
        { value: 'low_managed', label: 'Faible et géré' },
        { value: 'moderate_partial', label: 'Modéré, gestion partielle' },
        { value: 'high', label: 'Élevé' },
        { value: 'very_high_unmanaged', label: 'Très élevé, non géré' },
      ]},
      { key: 'recycling_strategy', label: 'Stratégie de recyclage', type: 'select', options: [
        { value: 'full_circular', label: 'Économie circulaire complète' },
        { value: 'active_program', label: 'Programme actif' },
        { value: 'partial', label: 'Partielle' },
        { value: 'minimal', label: 'Minimale' },
        { value: 'none', label: 'Aucune' },
      ]},
    ],
  },
]

function initAnswers() {
  const a = {}
  STEPS.forEach((step) => {
    step.fields.forEach((f) => {
      if (f.type === 'text') a[f.key] = ''
      else a[f.key] = f.options[0].value
    })
  })
  return a
}

export default function DiagnosticPage() {
  const { profileId } = useParams()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState(initAnswers)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const currentStep = STEPS[step]
  const isLast = step === STEPS.length - 1

  const set = (key, value) => setAnswers((a) => ({ ...a, [key]: value }))

  const handleSubmit = async () => {
    setError(null)
    setSubmitting(true)
    try {
      await profilesApi.setAnswers(token, profileId, answers)
      navigate(`/profiles/${profileId}/scores`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-xl font-bold text-gray-900">Diagnostic de projet</h1>
          <button
            onClick={() => setAnswers(DEMO_ANSWERS)}
            className="text-xs text-primary-600 hover:underline font-medium"
          >
            Remplir avec données démo
          </button>
        </div>

        {/* Progress bar */}
        <div className="flex gap-1 mt-4">
          {STEPS.map((s, i) => (
            <div
              key={i}
              className={`flex-1 h-1.5 rounded-full transition-colors ${
                i <= step ? 'bg-primary-600' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Étape {step + 1}/{STEPS.length} — {currentStep.title}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-5">
        <h2 className="font-semibold text-gray-800 text-lg">{currentStep.title}</h2>

        {currentStep.fields.map((field) => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{field.label}</label>
            {field.type === 'text' ? (
              <input
                type="text"
                value={answers[field.key] ?? ''}
                onChange={(e) => set(field.key, e.target.value)}
                placeholder={field.placeholder}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            ) : (
              <select
                value={String(answers[field.key])}
                onChange={(e) => {
                  const raw = e.target.value
                  let val = raw
                  if (raw === 'true') val = true
                  else if (raw === 'false') val = false
                  else if (!isNaN(raw) && raw !== '') val = Number(raw)
                  set(field.key, val)
                }}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
              >
                {field.options.map((opt) => (
                  <option key={String(opt.value)} value={String(opt.value)}>{opt.label}</option>
                ))}
              </select>
            )}
          </div>
        ))}
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex justify-between mt-6">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="border border-gray-300 text-gray-700 font-medium px-5 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors text-sm"
        >
          Précédent
        </button>

        {isLast ? (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-medium px-6 py-2 rounded-lg transition-colors text-sm flex items-center gap-2"
          >
            {submitting && <Spinner size="sm" />}
            {submitting ? 'Envoi...' : 'Soumettre et lancer le scoring'}
          </button>
        ) : (
          <button
            onClick={() => setStep((s) => s + 1)}
            className="bg-primary-600 hover:bg-primary-700 text-white font-medium px-6 py-2 rounded-lg transition-colors text-sm"
          >
            Suivant
          </button>
        )}
      </div>
    </div>
  )
}
