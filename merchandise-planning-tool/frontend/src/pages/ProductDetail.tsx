import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { KpiCard } from '../components/KpiCard'
import { ForecastChart } from '../components/ForecastChart'
import { fmtCurrency, fmtNumber, fmtPct } from '../format'
import type { Product, ProductForecast, Recommendation } from '../types'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const [product, setProduct] = useState<Product | null>(null)
  const [forecast, setForecast] = useState<ProductForecast | null>(null)
  const [rec, setRec] = useState<Recommendation | null>(null)

  useEffect(() => {
    if (!productId) return
    api.product(productId).then(setProduct)
    api.productForecast(productId).then(setForecast)
    api.buyingRecommendations().then((all) => setRec(all.find((r) => r.product_id === productId) ?? null))
  }, [productId])

  if (!product || !forecast) {
    return <div className="py-20 text-center text-sm text-slate-400">Loading…</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/buying" className="text-xs text-brand-600 hover:underline dark:text-brand-300">
          ← Back to buying recommendations
        </Link>
        <h1 className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">
          {product.name} <span className="text-sm font-normal text-slate-400">{product.product_id}</span>
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {product.category} · {fmtCurrency(product.retail_price)} retail / {fmtCurrency(product.unit_cost)} cost
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="On Hand" value={`${fmtNumber(product.current_inventory_units)} u`} />
        <KpiCard label="Lead Time" value={`${product.lead_time_weeks} wks`} />
        <KpiCard label="Target WOS" value={product.target_wos.toFixed(1)} />
        <KpiCard
          label="AI Forecast Accuracy"
          value={fmtPct(forecast.accuracy_pct)}
          sublabel="1 − WAPE, 8-week backtest"
        />
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">
          12-Week Demand Forecast
        </h2>
        <ForecastChart history={forecast.history} forecast={forecast.forecast} />
      </div>

      {rec && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h2 className="mb-3 text-sm font-semibold text-slate-900 dark:text-white">Buy Recommendation</h2>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Action</div>
              <div className="font-medium text-slate-800 dark:text-slate-200">{rec.action}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Recommended Order</div>
              <div className="font-medium text-slate-800 dark:text-slate-200">
                {fmtNumber(rec.recommended_order_units)} u ({fmtCurrency(rec.recommended_order_cost, true)})
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Forecasted Demand (coverage window)</div>
              <div className="font-medium text-slate-800 dark:text-slate-200">
                {fmtNumber(rec.forecast_demand_units)} u
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400">Safety Stock</div>
              <div className="font-medium text-slate-800 dark:text-slate-200">
                {fmtNumber(rec.safety_stock_units)} u
              </div>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{rec.reason}</p>
        </div>
      )}
    </div>
  )
}
