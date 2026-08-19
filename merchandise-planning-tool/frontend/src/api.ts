import type {
  BuyingSummary,
  KpiSummary,
  Product,
  ProductForecast,
  Recommendation,
  TrendPoint,
} from './types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  categories: () => get<string[]>('/categories'),
  products: () => get<Product[]>('/products'),
  product: (id: string) => get<Product>(`/products/${id}`),
  kpiSummary: (periodWeeks = 13) => get<KpiSummary>(`/kpis/summary?period_weeks=${periodWeeks}`),
  kpiByCategory: (periodWeeks = 13) => get<KpiSummary[]>(`/kpis/by-category?period_weeks=${periodWeeks}`),
  kpiTrend: (weeks = 26, category?: string) =>
    get<TrendPoint[]>(`/kpis/trend?weeks=${weeks}${category ? `&category=${encodeURIComponent(category)}` : ''}`),
  productForecast: (id: string) => get<ProductForecast>(`/products/${id}/forecast`),
  buyingRecommendations: (category?: string, action?: string) =>
    get<Recommendation[]>(
      `/buying/recommendations?${category ? `category=${encodeURIComponent(category)}&` : ''}${
        action ? `action=${encodeURIComponent(action)}` : ''
      }`,
    ),
  buyingSummary: () => get<BuyingSummary>('/buying/summary'),
}
