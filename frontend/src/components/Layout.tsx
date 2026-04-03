import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { authStore } from '../store/auth'
import {
  LayoutDashboard, Package, ShoppingCart, BarChart3, LogOut, Mountain, Sparkles
} from 'lucide-react'

const STORES = [
  { id: 'b1000000-0000-0000-0000-000000000001', name: 'NYC Flagship' },
  { id: 'b1000000-0000-0000-0000-000000000002', name: 'Boston Outlet' },
  { id: 'b1000000-0000-0000-0000-000000000003', name: 'London Central' },
]

export const STORE_MAP = Object.fromEntries(STORES.map(s => [s.id, s.name]))

const ROLE_LABELS: Record<string, string> = {
  regional_admin:   'Regional Admin',
  store_manager:    'Store Manager',
  sales_associate:  'Sales Associate',
}

const ROLE_COLORS: Record<string, string> = {
  regional_admin:  'bg-sky-500/20 text-sky-300 border-sky-700/50',
  store_manager:   'bg-violet-500/20 text-violet-300 border-violet-700/50',
  sales_associate: 'bg-emerald-500/20 text-emerald-300 border-emerald-700/50',
}

export default function Layout() {
  const navigate = useNavigate()
  const user = authStore.getUser()

  const navItems = [
    { to: '/',          label: 'Dashboard',    icon: LayoutDashboard },
    { to: '/inventory', label: 'Inventory',    icon: Package },
    { to: '/pos',       label: 'Point of Sale', icon: ShoppingCart },
    { to: '/reports',   label: 'Reports & AI', icon: BarChart3,
      hidden: user?.role === 'sales_associate' },
  ]

  const roleKey = user?.role ?? ''

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0">
        {/* Brand */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5 mb-0.5">
            <div className="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shadow-sm">
              <Mountain size={16} className="text-white" />
            </div>
            <span className="font-bold text-base tracking-tight text-white">NorthStar</span>
          </div>
          <p className="text-xs text-slate-500 ml-10">Operations Platform</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {navItems.filter(n => !n.hidden).map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                 ${isActive
                   ? 'bg-sky-600 text-white shadow-sm'
                   : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`
              }
            >
              <Icon size={17} />
              {label}
              {label === 'Reports & AI' && (
                <Sparkles size={12} className="ml-auto text-violet-400 opacity-70" />
              )}
            </NavLink>
          ))}
        </nav>

        {/* User info */}
        <div className="px-4 py-4 border-t border-slate-800 space-y-3">
          <div className="px-1 space-y-1.5">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${ROLE_COLORS[roleKey] ?? 'bg-slate-700 text-slate-300 border-slate-600'}`}>
              {ROLE_LABELS[roleKey] ?? roleKey}
            </span>
            <p className="text-xs text-slate-400 truncate">
              {user?.store_id ? STORE_MAP[user.store_id] ?? 'Unknown store' : 'All stores · 3 locations'}
            </p>
          </div>
          <button
            onClick={() => { authStore.logout(); navigate('/login') }}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-slate-950">
        <Outlet />
      </main>
    </div>
  )
}
