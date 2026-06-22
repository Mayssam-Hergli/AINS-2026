export default function Spinner({ size = 'md' }) {
  const s = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-10 w-10' : 'h-7 w-7'
  return (
    <div className={`${s} animate-spin rounded-full border-2 border-gray-200 border-t-primary-600`} />
  )
}
