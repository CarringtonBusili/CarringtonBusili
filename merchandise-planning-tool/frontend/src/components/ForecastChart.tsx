import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { chrome, useIsDark } from '../colors'
import type { ForecastPoint, HistoryPoint } from '../types'
import { fmtNumber } from '../format'

interface Row {
  week_index: number
  actual?: number
  forecast?: number
  band_base?: number
  band_range?: number
}

export function ForecastChart({ history, forecast }: { history: HistoryPoint[]; forecast: ForecastPoint[] }) {
  const isDark = useIsDark()
  const c = isDark ? chrome.dark : chrome.light
  const actualColor = isDark ? '#c3c2b7' : '#52514e'
  const forecastColor = isDark ? '#3987e5' : '#2a78d6'

  const recentHistory = history.slice(-26)
  const rows: Row[] = recentHistory.map((h) => ({ week_index: h.week_index, actual: h.units_sold }))

  const bridge = recentHistory[recentHistory.length - 1]
  if (bridge) {
    rows.push({ week_index: bridge.week_index, forecast: bridge.units_sold })
  }

  forecast.forEach((f) => {
    rows.push({
      week_index: f.week_index,
      forecast: f.forecast_units,
      band_base: f.low_90,
      band_range: f.high_90 - f.low_90,
    })
  })

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.gridline} vertical={false} />
        <XAxis
          dataKey="week_index"
          tick={{ fill: c.mutedInk, fontSize: 12 }}
          axisLine={{ stroke: c.baseline }}
          tickLine={false}
          tickFormatter={(w) => `W${w}`}
          minTickGap={20}
        />
        <YAxis
          tick={{ fill: c.mutedInk, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: c.surface,
            border: `1px solid ${c.gridline}`,
            borderRadius: 8,
            fontSize: 12,
            color: c.primaryInk,
          }}
          labelFormatter={(w) => `Week ${w}`}
          formatter={(value: number, name: string) =>
            name === 'band_base' || name === 'band_range' ? [null, null] : [fmtNumber(value), name]
          }
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: c.secondaryInk }}
          payload={[
            { value: 'Actual units', type: 'line', color: actualColor },
            { value: 'AI forecast', type: 'line', color: forecastColor },
            { value: '90% confidence', type: 'rect', color: isDark ? '#3987e533' : '#2a78d633' },
          ]}
        />
        <Area
          dataKey="band_base"
          stackId="band"
          stroke="none"
          fill="transparent"
          isAnimationActive={false}
          legendType="none"
        />
        <Area
          dataKey="band_range"
          stackId="band"
          stroke="none"
          fill={forecastColor}
          fillOpacity={0.15}
          isAnimationActive={false}
          legendType="none"
        />
        <Line
          type="monotone"
          dataKey="actual"
          name="Actual units"
          stroke={actualColor}
          strokeWidth={2}
          dot={false}
          connectNulls={false}
        />
        <Line
          type="monotone"
          dataKey="forecast"
          name="AI forecast"
          stroke={forecastColor}
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={false}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
