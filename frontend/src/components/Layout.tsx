import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { authStore } from '../store/auth'
import {
  LayoutDashboard, Package, ShoppingCart, BarChart3, LogOut, Mountain, Sparkles, Menu, X
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
  const location = useLocation()
  const user = authStore.getUser()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  // Close menu on navigation on mobile
  useEffect(() => {
    setIsMenuOpen(false)
  }, [location.pathname])

  const navItems = [
    { to: '/',          label: 'Dashboard',    icon: LayoutDashboard },
    { to: '/inventory', label: 'Inventory',    icon: Package },
    { to: '/pos',       label: 'Point of Sale', icon: ShoppingCart },
    { to: '/reports',   label: 'Reports & AI', icon: BarChart3,
      hidden: user?.role === 'sales_associate' },
  ]

  const roleKey = user?.role ?? ''

  return (
    <div className="flex flex-col lg:flex-row h-screen overflow-hidden bg-slate-950">
      {/* Mobile Header */}
      <header className="lg:hidden h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-5 shrink-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shadow-sm">
            <Mountain size={16} className="text-white" />
          </div>
          <span className="font-bold text-base tracking-tight text-white uppercase italic">NorthStar</span>
        </div>
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Toggle menu"
        >
          {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {/* Sidebar Mobile Overlay */}
      {isMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 z-50 transition-transform duration-300
        ${isMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Brand (Desktop only) */}
        <div className="hidden lg:block px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5 mb-0.5">
            <div className="w-8 h-8 bg-sky-600 rounded-lg flex items-center justify-center shadow-sm">
              <Mountain size={16} className="text-white" />
            </div>
            <span className="font-bold text-base tracking-tight text-white">NorthStar</span>
          </div>
          <p className="text-xs text-slate-500 ml-10">Operations Platform</p>
        </div>

        {/* Brand (Mobile top) */}
        <div className="lg:hidden px-5 py-5 border-b border-slate-800 flex items-center justify-between">
           <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Navigation</span>
           <button onClick={() => setIsMenuOpen(false)} className="text-slate-500 hover:text-white lg:hidden">
              <X size={18} />
           </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
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
        <div className="px-4 py-4 border-t border-slate-800 space-y-3 bg-slate-900/50">
          <div className="px-1 space-y-1.5 text-center lg:text-left">
            <div className="flex lg:inline-flex justify-center lg:justify-start">
              <span className={`inline-flex items-center px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${ROLE_COLORS[roleKey] ?? 'bg-slate-700 text-slate-300 border-slate-600'}`}>
                {ROLE_LABELS[roleKey] ?? roleKey}
              </span>
            </div>
            <p className="text-xs text-slate-400 truncate">
              {user?.store_id ? STORE_MAP[user.store_id] ?? 'Unknown store' : 'All stores · 3 locations'}
            </p>
          </div>
          <button
            onClick={() => { authStore.logout(); navigate('/login') }}
            className="flex items-center justify-center lg:justify-start gap-2 w-full px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors border border-transparent hover:border-red-900/40"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 overflow-auto bg-slate-950 relative flex flex-col pt-0 lg:pt-0">
        <div className="flex-1 w-full max-w-full overflow-x-hidden">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
