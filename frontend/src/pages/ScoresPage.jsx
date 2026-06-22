import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { scoresApi } from '../api/scores'
import ScoreCard from '../components/ScoreCard'
import AnomalyCard from '../components/AnomalyCard'
import Spinner from '../components/Spinner'

const DIMENSIONS = ['market', 'commercial', 'innovation', 'scalability', 'green']

export default function ScoresPage() {
  const { profileId } = useParams()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [computing, setComputing] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    scoresApi.get(token, profileId)
      .then(setData)
      .catch((err) => {
        if (err.status !== 404) setError(err.message)
        // 404 = not yet scored; show "compute" button
      })
      .finally(() => setLoading(false))
  }, [token, profileId])

  const handleCompute = async () => {
    setError(null)
    setComputing(true)
    try {
      const result = await scoresApi.compute(token, profileId)
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setComputing(false)
    }
  }

  if (loading) return <div className="flex justify-center py-20"><Spinner size="lg" /></div>

  // Not yet scored
  if (!data && !error) return (
    <div className="max-w-xl mx-auto text-center py-20">
      <div className="text-5xl mb-4">📊</div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">Scores non calculés</h2>
      <p className="text-gray-500 text-sm mb-6">
        Lancez l'agent de scoring MS2 pour analyser ce projet.<br />
        L'opération prend environ 30 à 60 secondes.
      </p>
      {error && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      <div className="flex gap-3 justify-center">
        <button
          onClick={() => navigate(`/profiles/${profileId}/diagnostic`)}
          className="border border-gray-300 text-gray-700 font-medium px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm"
        >
          Modifier le diagnostic
        </button>
        <button
          onClick={handleCompute}
          disabled={computing}
          className="bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white font-medium px-6 py-2.5 rounded-lg transition-colors flex items-center gap-2 text-sm"
        >
          {computing && <Spinner size="sm" />}
          {computing ? 'Analyse en cours...' : 'Calculer les scores'}
        </button>
      </div>
      {computing && (
        <p className="mt-4 text-xs text-gray-400">
          L'agent IA analyse les 5 dimensions de votre projet...
        </p>
      )}
    </div>
  )

  if (error && !data) return (
    <div className="max-w-xl mx-auto text-center py-20">
      <p className="text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm">{error}</p>
      <button onClick={() => navigate('/dashboard')} className="mt-4 text-sm text-primary-600 hover:underline">
        Retour au tableau de bord
      </button>
    </div>
  )

  const anomalies = data?.anomaly_flags || []
  const lowDims = data?.low_scoring_dimensions || []

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Résultats du scoring</h1>
          {lowDims.length > 0 && (
            <p className="text-sm text-gray-500 mt-1">
              Dimensions faibles : {lowDims.join(', ')}
            </p>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/profiles/${profileId}/roadmap`)}
            className="border border-gray-300 text-gray-600 text-sm font-medium px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Voir la roadmap
          </button>
          <button
            onClick={handleCompute}
            disabled={computing}
            className="bg-primary-600 hover:bg-primary-700 disabled:opacity-60 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            {computing && <Spinner size="sm" />}
            {computing ? 'Recalcul...' : 'Recalculer'}
          </button>
        </div>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {DIMENSIONS.map((dim) => (
          <div key={dim} className={dim === 'green' ? 'md:col-span-2' : ''}>
            <ScoreCard dimension={dim} data={data?.scores?.[dim]} />
          </div>
        ))}
      </div>

      {/* Anomaly flags */}
      {anomalies.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">Signaux d'alerte détectés</h2>
          {anomalies.map((flag, i) => (
            <AnomalyCard key={i} flag={flag} />
          ))}
        </div>
      )}

      {/* Anomaly summary */}
      {data?.anomaly_summary && (
        <div className="bg-gray-50 rounded-xl border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Analyse des signaux</h2>
          <p className="text-sm text-gray-600 leading-relaxed">{data.anomaly_summary}</p>
        </div>
      )}

      {/* Justifications */}
      {data?.justifications && Object.keys(data.justifications).length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-800">Justifications détaillées</h2>
          {Object.entries(data.justifications).map(([dim, j]) => (
            <details key={dim} className="bg-white rounded-xl border border-gray-100 shadow-sm">
              <summary className="px-5 py-4 cursor-pointer font-medium text-gray-700 text-sm capitalize hover:text-primary-600">
                {dim}
              </summary>
              <div className="px-5 pb-4 space-y-2 text-sm text-gray-600 border-t border-gray-50 pt-3">
                {j.text && <p>{j.text}</p>}
                {j.improvement_action && (
                  <p className="text-primary-700 font-medium">
                    Action recommandée : {j.improvement_action}
                  </p>
                )}
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}
