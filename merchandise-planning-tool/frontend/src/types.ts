export interface KpiSummary {
  period_weeks: number
  revenue: number
  gross_margin: number
  gross_margin_pct: number
  units_sold: number
  sell_through_pct: number
  gmroi: number
  inventory_turnover: number
  weeks_of_supply: number
  markdown_pct: number
  sales_plan_variance_pct: number
  stockout_rate_pct: number
  ending_inventory_units: number
  ending_inventory_cost_value: number
  category?: string
}

export interface TrendPoint {
  week_index: number
  revenue: number
  planned_units: number
  units_sold: number
  gross_margin: number
  gross_margin_pct: number
  ending_inventory: number
  stockouts: number
  week_of_year: number
}

export interface Product {
  product_id: string
  name: string
  category: string
  retail_price: number
  unit_cost: number
  lead_time_weeks: number
  target_wos: number
  reorder_cycle_weeks: number
  current_inventory_units: number
}

export interface Recommendation {
  product_id: string
  name: string
  category: string
  lead_time_weeks: number
  review_period_weeks: number
  current_inventory_units: number
  current_weeks_of_supply: number
  target_weeks_of_supply: number
  forecast_demand_units: number
  safety_stock_units: number
  recommended_order_units: number
  recommended_order_cost: number
  recommended_order_retail_value: number
  momentum_pct: number
  action: 'Urgent Buy' | 'Buy' | 'On Track' | 'Hold / Markdown'
  reason: string
  forecast_wape: number
}

export interface BuyingSummary {
  total_recommended_spend: number
  sku_count: number
  by_action: Record<string, { count: number; cost: number }>
  avg_forecast_accuracy_pct: number
}

export interface ForecastPoint {
  week_index: number
  week_of_year: number
  weeks_ahead: number
  forecast_units: number
  low_90: number
  high_90: number
}

export interface HistoryPoint {
  week_index: number
  week_of_year: number
  units_sold: number
  weeks_ago: number
}

export interface ProductForecast {
  product_id: string
  wape: number
  accuracy_pct: number
  residual_std: number
  history: HistoryPoint[]
  forecast: ForecastPoint[]
}
