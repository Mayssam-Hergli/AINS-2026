export default function AssistantPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Assistant</h1>
        <p className="text-gray-500 text-sm mt-1">
          Assistant conversationnel trilingue (FR / AR / Darija)
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 text-sm text-amber-800">
        <strong>Module en cours d'intégration</strong> — L'assistant sera ancré dans votre profil
        diagnostic + scores + base de connaissances. Aucune réponse générique — tout sera contextualisé
        à votre projet.
      </div>

      {/* Chat UI skeleton */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 bg-gray-50">
          <p className="text-sm font-medium text-gray-700">Conversation</p>
        </div>
        <div className="h-72 flex items-center justify-center text-gray-400 text-sm">
          L'assistant sera disponible après l'intégration de MS3
        </div>
        <div className="px-4 py-3 border-t border-gray-100 flex gap-2">
          <input
            disabled
            className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-400 cursor-not-allowed"
            placeholder="Posez votre question en français, arabe ou darija..."
          />
          <button
            disabled
            className="bg-primary-600 opacity-40 text-white px-4 py-2 rounded-lg text-sm font-medium cursor-not-allowed"
          >
            Envoyer
          </button>
        </div>
      </div>
    </div>
  )
}
