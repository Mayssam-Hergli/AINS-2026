import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { profilesApi } from '../api/profiles'
import Spinner from '../components/Spinner'

const STATUS_CONFIG = {
  pending: {
    label: 'Diagnostic en attente',
    color: 'bg-gray-100 text-gray-600',
    action: 'Démarrer le diagnostic',
    actionPath: (id) => `/profiles/${id}/diagnostic`,
  },
  diagnostic_complete: {
    label: 'Prêt pour le scoring',
    color: 'bg-blue-100 text-blue-700',
    action: 'Lancer le scoring',
    actionPath: (id) => `/profiles/${id}/scores`,
  },
  scored: {
    label: 'Scores calculés',
    color: 'bg-green-100 text-green-700',
    action: 'Voir les scores',
    actionPath: (id) => `/profiles/${id}/scores`,
  },
}

function NewProfileModal({ onClose, onCreated, token }) {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setLoading(true)
    setError(null)
    try {
      const profile = await profilesApi.create(token, name.trim())
      onCreated(profile)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Nouveau projet</h3>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom du projet</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="ex. EcoTextile Sfax"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-700 font-medium py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="flex-1 bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-medium py-2 rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
            >
              {loading && <Spinner size="sm" />}
              Créer
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    profilesApi.list(token)
      .then(setProfiles)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [token])

  const handleCreated = (profile) => {
    setShowModal(false)
    navigate(`/profiles/${profile.id}/diagnostic`)
  }

  if (loading) return (
    <div className="flex justify-center py-20"><Spinner size="lg" /></div>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mes projets</h1>
          <p className="text-gray-500 text-sm mt-1">{profiles.length} projet{profiles.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-primary-600 hover:bg-primary-700 text-white font-medium px-4 py-2 rounded-lg transition-colors text-sm flex items-center gap-2"
        >
          <span>+</span> Nouveau projet
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-6">
          {error}
        </div>
      )}

      {profiles.length === 0 && !error ? (
        <div className="text-center py-20 border-2 border-dashed border-gray-200 rounded-2xl">
          <p className="text-gray-500 mb-4">Aucun projet pour le moment.</p>
          <button
            onClick={() => setShowModal(true)}
            className="bg-primary-600 hover:bg-primary-700 text-white font-medium px-6 py-2.5 rounded-lg transition-colors text-sm"
          >
            Créer mon premier projet
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((p) => {
            const cfg = STATUS_CONFIG[p.status] || STATUS_CONFIG.pending
            return (
              <div key={p.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex flex-col gap-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-gray-800 line-clamp-2">{p.name}</h3>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0 ${cfg.color}`}>
                    {cfg.label}
                  </span>
                </div>
                <p className="text-xs text-gray-400">
                  Créé le {new Date(p.created_at).toLocaleDateString('fr-TN', { day: 'numeric', month: 'long', year: 'numeric' })}
                </p>
                <div className="mt-auto flex gap-2">
                  <button
                    onClick={() => navigate(cfg.actionPath(p.id))}
                    className="flex-1 bg-primary-600 hover:bg-primary-700 text-white text-xs font-medium py-2 rounded-lg transition-colors"
                  >
                    {cfg.action}
                  </button>
                  {p.status === 'scored' && (
                    <button
                      onClick={() => navigate(`/profiles/${p.id}/roadmap`)}
                      className="flex-1 border border-gray-200 text-gray-600 hover:bg-gray-50 text-xs font-medium py-2 rounded-lg transition-colors"
                    >
                      Roadmap
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showModal && (
        <NewProfileModal
          token={token}
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}
