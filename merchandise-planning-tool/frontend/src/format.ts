export const fmtCurrency = (v: number, compact = false) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact ? 'compact' : 'standard',
  }).format(v)

export const fmtPct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`

export const fmtNumber = (v: number, compact = false) =>
  new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 1,
    notation: compact ? 'compact' : 'standard',
  }).format(v)
