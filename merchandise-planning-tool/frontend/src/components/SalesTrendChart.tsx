import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { chrome, useIsDark } from '../colors'
import type { TrendPoint } from '../types'
import { fmtNumber } from '../format'

export function SalesTrendChart({ data }: { data: TrendPoint[] }) {
  const isDark = useIsDark()
  const c = isDark ? chrome.dark : chrome.light
  const seriesActual = isDark ? '#3987e5' : '#2a78d6'
  const seriesPlan = isDark ? '#898781' : '#898781'

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={c.gridline} vertical={false} />
        <XAxis
          dataKey="week_index"
          tick={{ fill: c.mutedInk, fontSize: 12 }}
          axisLine={{ stroke: c.baseline }}
          tickLine={false}
          tickFormatter={(w) => `W${w}`}
          minTickGap={24}
        />
        <YAxis
          tick={{ fill: c.mutedInk, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={(v) => fmtNumber(v, true)}
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
          formatter={(value: number, name: string) => [fmtNumber(value), name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: c.secondaryInk }} />
        <Line
          type="monotone"
          dataKey="units_sold"
          name="Actual units"
          stroke={seriesActual}
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="planned_units"
          name="Planned units"
          stroke={seriesPlan}
          strokeWidth={2}
          strokeDasharray="4 3"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
