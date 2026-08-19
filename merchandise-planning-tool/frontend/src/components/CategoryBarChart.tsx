import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { categorical, chrome, useIsDark } from '../colors'
import type { KpiSummary } from '../types'
import { fmtCurrency } from '../format'

export function CategoryBarChart({ data }: { data: KpiSummary[] }) {
  const isDark = useIsDark()
  const c = isDark ? chrome.dark : chrome.light
  const colors = isDark ? categorical.dark : categorical.light

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={c.gridline} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: c.mutedInk, fontSize: 12 }}
          axisLine={{ stroke: c.baseline }}
          tickLine={false}
          tickFormatter={(v) => fmtCurrency(v, true)}
        />
        <YAxis
          type="category"
          dataKey="category"
          tick={{ fill: c.secondaryInk, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={90}
        />
        <Tooltip
          contentStyle={{
            background: c.surface,
            border: `1px solid ${c.gridline}`,
            borderRadius: 8,
            fontSize: 12,
            color: c.primaryInk,
          }}
          formatter={(value: number) => fmtCurrency(value)}
        />
        <Bar dataKey="revenue" radius={[0, 4, 4, 0]} maxBarSize={22}>
          {data.map((entry, i) => (
            <Cell key={entry.category} fill={colors[i % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
