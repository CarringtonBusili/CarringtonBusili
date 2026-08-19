import { useEffect, useState } from 'react'

export const categorical = {
  light: ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#eb6834'],
  dark: ['#3987e5', '#008300', '#d55181', '#c98500', '#199e70', '#d95926'],
}

export const status = {
  'Urgent Buy': { light: '#d03b3b', dark: '#d03b3b', label: 'Urgent Buy' },
  Buy: { light: '#fab219', dark: '#fab219', label: 'Buy' },
  'On Track': { light: '#0ca30c', dark: '#0ca30c', label: 'On Track' },
  'Hold / Markdown': { light: '#ec835a', dark: '#ec835a', label: 'Hold / Markdown' },
} as const

export const chrome = {
  light: {
    surface: '#fcfcfb',
    primaryInk: '#0b0b0b',
    secondaryInk: '#52514e',
    mutedInk: '#898781',
    gridline: '#e1e0d9',
    baseline: '#c3c2b7',
  },
  dark: {
    surface: '#1a1a19',
    primaryInk: '#ffffff',
    secondaryInk: '#c3c2b7',
    mutedInk: '#898781',
    gridline: '#2c2c2a',
    baseline: '#383835',
  },
}

export function useIsDark(): boolean {
  const query = typeof window !== 'undefined' ? window.matchMedia('(prefers-color-scheme: dark)') : null
  const [isDark, setIsDark] = useState(query?.matches ?? false)

  useEffect(() => {
    if (!query) return
    const listener = (e: MediaQueryListEvent) => setIsDark(e.matches)
    query.addEventListener('change', listener)
    return () => query.removeEventListener('change', listener)
  }, [query])

  return isDark
}
