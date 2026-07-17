import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Buying from './pages/Buying'
import ProductDetail from './pages/ProductDetail'

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-brand-600 text-white'
            : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              MP
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900 dark:text-white">
                Merchandise Planning &amp; Buying
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                Merchandise Financial Planning
              </div>
            </div>
          </div>
          <nav className="flex gap-1">
            <NavItem to="/" label="Overview" />
            <NavItem to="/buying" label="AI Buying" />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/buying" element={<Buying />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
        </Routes>
      </main>
    </div>
  )
}
