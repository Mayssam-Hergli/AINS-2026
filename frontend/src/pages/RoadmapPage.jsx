import { useParams } from 'react-router-dom'

const HORIZONS = [
  {
    label: 'Immédiat (0–1 mois)',
    color: 'bg-red-50 border-red-200',
    tag: 'bg-red-100 text-red-700',
    items: [
      'Compléter la validation de l\'adéquation offre-besoin',
      'Documenter 3 études de cas clients pour le pitch',
      'Définir les KPIs de rétention pour l\'étape seed',
    ],
  },
  {
    label: 'Court terme (1–3 mois)',
    color: 'bg-yellow-50 border-yellow-200',
    tag: 'bg-yellow-100 text-yellow-700',
    items: [
      'Déposer la demande de brevet auprès de l\'INNORPI',
      'Lancer un pilote dans 2 gouvernorats supplémentaires',
      'Préparer le dossier d\'éligibilité Startup Act',
    ],
  },
  {
    label: 'Moyen terme (3–6 mois)',
    color: 'bg-green-50 border-green-200',
    tag: 'bg-green-100 text-green-700',
    items: [
      'Intégrer un partenariat avec BFPME pour le financement',
      'Développer la version Arabic/Darija de l\'interface',
      'Obtenir la certification ISO 14001 (impact environnemental)',
    ],
  },
]

export default function RoadmapPage() {
  const { profileId } = useParams()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Roadmap</h1>
        <p className="text-gray-500 text-sm mt-1">
          Générée par MS3 (RAG anchré dans 41+ ressources tunisiennes) — module en cours d'intégration
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 text-sm text-amber-800">
        <strong>Aperçu statique</strong> — Les données ci-dessous sont un exemple illustratif.
        La roadmap réelle sera générée automatiquement par l'agent MS3 en fonction de vos scores
        une fois le module intégré.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {HORIZONS.map((h) => (
          <div key={h.label} className={`rounded-xl border p-5 ${h.color}`}>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${h.tag}`}>
              {h.label}
            </span>
            <ul className="mt-4 space-y-3">
              {h.items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 flex-shrink-0 text-gray-400">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 text-center">
        Chaque recommandation citée par MS3 inclura sa source (APII, BFPME, Startup Act, ANPE...)
      </p>
    </div>
  )
}
