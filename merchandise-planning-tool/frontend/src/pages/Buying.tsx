import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { KpiCard } from '../components/KpiCard'
import { status as statusColors, useIsDark } from '../colors'
import { fmtCurrency, fmtNumber, fmtPct } from '../format'
import type { BuyingSummary, Recommendation } from '../types'

const ACTIONS = ['Urgent Buy', 'Buy', 'On Track', 'Hold / Markdown'] as const

function ActionBadge({ action }: { action: Recommendation['action'] }) {
  const isDark = useIsDark()
  const color = statusColors[action][isDark ? 'dark' : 'light']
  const icon =
    action === 'Urgent Buy' ? '⛔' : action === 'Buy' ? '⬆' : action === 'On Track' ? '✓' : '⏸'
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ color, backgroundColor: `${color}1a` }}
    >
      <span aria-hidden>{icon}</span>
      {action}
    </span>
  )
}

export default function Buying() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [summary, setSummary] = useState<BuyingSummary | null>(null)
  const [categories, setCategories] = useState<string[]>([])
  const [category, setCategory] = useState<string>('')
  const [action, setAction] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.categories().then(setCategories)
    api.buyingSummary().then(setSummary)
  }, [])

  useEffect(() => {
    setLoading(true)
    api.buyingRecommendations(category || undefined, action || undefined).then((d) => {
      setRecs(d)
      setLoading(false)
    })
  }, [category, action])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-white">AI Buying Recommendations</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Demand forecast (gradient-boosted regressor + seasonal baseline) blended into an
          open-to-buy recommendation per SKU: forecast over lead time + reorder cycle, plus safety
          stock, minus on-hand inventory.
        </p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Recommended Spend" value={fmtCurrency(summary.total_recommended_spend, true)} />
          <KpiCard label="SKUs Tracked" value={fmtNumber(summary.sku_count)} />
          <KpiCard
            label="Avg. Forecast Accuracy"
            value={fmtPct(summary.avg_forecast_accuracy_pct)}
            sublabel="1 − WAPE, 8-week backtest"
          />
          <KpiCard
            label="Urgent Buys"
            value={fmtNumber(summary.by_action['Urgent Buy']?.count ?? 0)}
            tone="critical"
            sublabel={fmtCurrency(summary.by_action['Urgent Buy']?.cost ?? 0, true)}
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <div className="flex gap-1">
          <button
            onClick={() => setAction('')}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
              action === ''
                ? 'bg-brand-600 text-white'
                : 'border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'
            }`}
          >
            All actions
          </button>
          {ACTIONS.map((a) => (
            <button
              key={a}
              onClick={() => setAction(a)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                action === a
                  ? 'bg-brand-600 text-white'
                  : 'border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                <th className="px-4 py-2 font-medium">Product</th>
                <th className="px-4 py-2 font-medium">Action</th>
                <th className="px-4 py-2 font-medium">On Hand</th>
                <th className="px-4 py-2 font-medium">WOS (cur / target)</th>
                <th className="px-4 py-2 font-medium">Momentum</th>
                <th className="px-4 py-2 font-medium">Recommended Qty</th>
                <th className="px-4 py-2 font-medium">Order Cost</th>
                <th className="px-4 py-2 font-medium">Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">
                    Loading recommendations…
                  </td>
                </tr>
              ) : (
                recs.map((r) => (
                  <tr
                    key={r.product_id}
                    className="border-b border-slate-50 tabular-nums last:border-0 dark:border-slate-800/60"
                  >
                    <td className="px-4 py-2">
                      <Link to={`/products/${r.product_id}`} className="font-medium text-brand-700 hover:underline dark:text-brand-300">
                        {r.name}
                      </Link>
                      <div className="text-xs text-slate-400">{r.category}</div>
                    </td>
                    <td className="px-4 py-2">
                      <ActionBadge action={r.action} />
                      <div className="mt-0.5 text-xs text-slate-400">{r.reason}</div>
                    </td>
                    <td className="px-4 py-2 text-slate-600 dark:text-slate-300">
                      {fmtNumber(r.current_inventory_units)}
                    </td>
                    <td className="px-4 py-2 text-slate-600 dark:text-slate-300">
                      {r.current_weeks_of_supply.toFixed(1)} / {r.target_weeks_of_supply.toFixed(1)}
                    </td>
                    <td
                      className={`px-4 py-2 font-medium ${
                        r.momentum_pct > 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {r.momentum_pct > 0 ? '▲' : '▼'} {fmtPct(Math.abs(r.momentum_pct))}
                    </td>
                    <td className="px-4 py-2 font-medium text-slate-800 dark:text-slate-200">
                      {fmtNumber(r.recommended_order_units)} u
                    </td>
                    <td className="px-4 py-2 text-slate-600 dark:text-slate-300">
                      {fmtCurrency(r.recommended_order_cost, true)}
                    </td>
                    <td className="px-4 py-2 text-slate-600 dark:text-slate-300">
                      {fmtPct(1 - r.forecast_wape)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
