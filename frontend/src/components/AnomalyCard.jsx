const SEVERITY_STYLES = {
  high: {
    container: 'bg-red-50 border-red-200',
    badge: 'bg-red-100 text-red-700',
    icon: '⚠️',
    label: 'Critique',
  },
  medium: {
    container: 'bg-yellow-50 border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-700',
    icon: '⚡',
    label: 'Attention',
  },
  low: {
    container: 'bg-blue-50 border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    icon: 'ℹ️',
    label: 'Info',
  },
}

export default function AnomalyCard({ flag }) {
  const style = SEVERITY_STYLES[flag.severity] || SEVERITY_STYLES.low
  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border ${style.container}`}>
      <span className="text-lg flex-shrink-0">{style.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${style.badge}`}>
            {style.label}
          </span>
          <code className="text-xs text-gray-500">{flag.code}</code>
        </div>
        <p className="text-sm text-gray-700">{flag.message}</p>
      </div>
    </div>
  )
}
