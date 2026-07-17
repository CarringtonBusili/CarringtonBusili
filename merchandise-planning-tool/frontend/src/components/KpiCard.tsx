interface KpiCardProps {
  label: string
  value: string
  sublabel?: string
  tone?: 'neutral' | 'good' | 'warning' | 'critical'
}

const toneClasses: Record<NonNullable<KpiCardProps['tone']>, string> = {
  neutral: 'text-slate-500 dark:text-slate-400',
  good: 'text-emerald-600 dark:text-emerald-400',
  warning: 'text-amber-600 dark:text-amber-400',
  critical: 'text-red-600 dark:text-red-400',
}

export function KpiCard({ label, value, sublabel, tone = 'neutral' }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </div>
      <div className="mt-1.5 text-2xl font-semibold tabular-nums text-slate-900 dark:text-white">
        {value}
      </div>
      {sublabel && <div className={`mt-1 text-xs font-medium ${toneClasses[tone]}`}>{sublabel}</div>}
    </div>
  )
}
