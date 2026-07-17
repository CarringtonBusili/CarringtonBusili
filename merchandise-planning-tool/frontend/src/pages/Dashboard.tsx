import { useEffect, useState } from 'react'
import { api } from '../api'
import { KpiCard } from '../components/KpiCard'
import { SalesTrendChart } from '../components/SalesTrendChart'
import { CategoryBarChart } from '../components/CategoryBarChart'
import { fmtCurrency, fmtNumber, fmtPct } from '../format'
import type { KpiSummary, TrendPoint } from '../types'

const PERIODS = [
  { label: '4 wks', weeks: 4 },
  { label: '13 wks', weeks: 13 },
  { label: '26 wks', weeks: 26 },
  { label: '52 wks', weeks: 52 },
]

export default function Dashboard() {
  const [periodWeeks, setPeriodWeeks] = useState(13)
  const [summary, setSummary] = useState<KpiSummary | null>(null)
  const [byCategory, setByCategory] = useState<KpiSummary[]>([])
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      api.kpiSummary(periodWeeks),
      api.kpiByCategory(periodWeeks),
      api.kpiTrend(Math.max(periodWeeks * 2, 26)),
    ]).then(([s, cat, tr]) => {
      if (cancelled) return
      setSummary(s)
      setByCategory(cat)
      setTrend(tr)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [periodWeeks])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-white">Planning Overview</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Merchandise financial planning KPIs across {byCategory.length || '—'} categories
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900">
          {PERIODS.map((p) => (
            <button
              key={p.weeks}
              onClick={() => setPeriodWeeks(p.weeks)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                periodWeeks === p.weeks
                  ? 'bg-brand-600 text-white'
                  : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading || !summary ? (
        <div className="py-20 text-center text-sm text-slate-400">Loading KPIs…</div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <KpiCard label="Revenue" value={fmtCurrency(summary.revenue, true)} />
            <KpiCard
              label="Gross Margin"
              value={fmtPct(summary.gross_margin_pct)}
              sublabel={fmtCurrency(summary.gross_margin, true)}
            />
            <KpiCard
              label="GMROI"
              value={`${summary.gmroi.toFixed(2)}x`}
              sublabel="margin $ / avg inventory $"
            />
            <KpiCard
              label="Inventory Turnover"
              value={`${summary.inventory_turnover.toFixed(2)}x`}
              sublabel="annualized"
            />
            <KpiCard
              label="Sell-Through"
              value={fmtPct(summary.sell_through_pct)}
              tone={summary.sell_through_pct < 0.5 ? 'warning' : 'good'}
            />
            <KpiCard
              label="Weeks of Supply"
              value={`${summary.weeks_of_supply.toFixed(1)}`}
              sublabel={`${fmtNumber(summary.ending_inventory_units)} units on hand`}
            />
            <KpiCard
              label="Markdown %"
              value={fmtPct(summary.markdown_pct)}
              tone={summary.markdown_pct > 0.15 ? 'warning' : 'neutral'}
            />
            <KpiCard
              label="Sales vs. Plan"
              value={fmtPct(summary.sales_plan_variance_pct)}
              tone={summary.sales_plan_variance_pct < 0 ? 'critical' : 'good'}
              sublabel={summary.sales_plan_variance_pct < 0 ? 'Behind plan' : 'Ahead of plan'}
            />
            <KpiCard
              label="Stockout Rate"
              value={fmtPct(summary.stockout_rate_pct)}
              tone={summary.stockout_rate_pct > 0.15 ? 'critical' : 'neutral'}
            />
            <KpiCard
              label="Inventory Value"
              value={fmtCurrency(summary.ending_inventory_cost_value, true)}
              sublabel="at cost"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-3">
              <h2 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">
                Weekly Sales: Actual vs. Plan
              </h2>
              <SalesTrendChart data={trend} />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 lg:col-span-2">
              <h2 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">
                Revenue by Category
              </h2>
              <CategoryBarChart data={byCategory} />
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h2 className="border-b border-slate-200 px-4 py-3 text-sm font-semibold text-slate-900 dark:border-slate-800 dark:text-white">
              Category Performance
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
                    <th className="px-4 py-2 font-medium">Category</th>
                    <th className="px-4 py-2 font-medium">Revenue</th>
                    <th className="px-4 py-2 font-medium">GM%</th>
                    <th className="px-4 py-2 font-medium">Sell-Through</th>
                    <th className="px-4 py-2 font-medium">GMROI</th>
                    <th className="px-4 py-2 font-medium">Turns</th>
                    <th className="px-4 py-2 font-medium">WOS</th>
                    <th className="px-4 py-2 font-medium">Markdown%</th>
                  </tr>
                </thead>
                <tbody>
                  {byCategory.map((c) => (
                    <tr
                      key={c.category}
                      className="border-b border-slate-50 tabular-nums last:border-0 dark:border-slate-800/60"
                    >
                      <td className="px-4 py-2 font-medium text-slate-800 dark:text-slate-200">{c.category}</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{fmtCurrency(c.revenue, true)}</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{fmtPct(c.gross_margin_pct)}</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{fmtPct(c.sell_through_pct)}</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{c.gmroi.toFixed(2)}x</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{c.inventory_turnover.toFixed(2)}x</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{c.weeks_of_supply.toFixed(1)}</td>
                      <td className="px-4 py-2 text-slate-600 dark:text-slate-300">{fmtPct(c.markdown_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
