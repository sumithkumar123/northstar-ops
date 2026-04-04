import { useState, useEffect, useRef } from 'react'
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

  // Touch-swipe state
  const touchStartX = useRef<number | null>(null)
  const touchStartY = useRef<number | null>(null)

  // Close menu on navigation
  useEffect(() => {
    setIsMenuOpen(false)
  }, [location.pathname])

  // Swipe-to-open: detect left→right swipe from edge
  useEffect(() => {
    const onTouchStart = (e: TouchEvent) => {
      touchStartX.current = e.touches[0].clientX
      touchStartY.current = e.touches[0].clientY
    }
    const onTouchEnd = (e: TouchEvent) => {
      if (touchStartX.current === null || touchStartY.current === null) return
      const dx = e.changedTouches[0].clientX - touchStartX.current
      const dy = Math.abs(e.changedTouches[0].clientY - touchStartY.current)
      // Open: swipe right from left edge (within 40px), displacement > 60px, mostly horizontal
      if (!isMenuOpen && touchStartX.current < 40 && dx > 60 && dy < 60) {
        setIsMenuOpen(true)
      }
      // Close: swipe left while open
      if (isMenuOpen && dx < -60 && dy < 60) {
        setIsMenuOpen(false)
      }
      touchStartX.current = null
      touchStartY.current = null
    }
    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchend', onTouchEnd, { passive: true })
    return () => {
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [isMenuOpen])

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
      <header className="lg:hidden h-14 bg-slate-900/95 backdrop-blur-md border-b border-slate-800/80 flex items-center justify-between px-4 shrink-0 z-50">
        <div className="flex items-center gap-2.5">
          {/* Logo mark */}
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-violet-600 flex items-center justify-center shadow-lg shadow-sky-900/40">
            <Mountain size={15} className="text-white" />
          </div>
          {/* Brand name — gradient, modern */}
          <span className="text-[17px] font-black tracking-tight bg-gradient-to-r from-sky-400 to-violet-400 bg-clip-text text-transparent select-none">
            NorthStar
          </span>
        </div>
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 active:scale-95 transition-all"
          aria-label="Toggle menu"
        >
          {isMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </header>

      {/* Sidebar Mobile Overlay — smooth fade */}
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300 ${
          isMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setIsMenuOpen(false)}
      />

      {/* Sidebar — smooth slide */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 w-72 bg-slate-900 border-r border-slate-800/80 flex flex-col shrink-0 z-50
        transition-transform duration-300 ease-in-out will-change-transform
        ${isMenuOpen ? 'translate-x-0 shadow-2xl shadow-black/50' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Brand — Desktop */}
        <div className="hidden lg:block px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5 mb-0.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-violet-600 flex items-center justify-center shadow-lg shadow-sky-900/40">
              <Mountain size={17} className="text-white" />
            </div>
            <span className="text-lg font-black tracking-tight bg-gradient-to-r from-sky-400 to-violet-400 bg-clip-text text-transparent select-none">
              NorthStar
            </span>
          </div>
          <p className="text-[11px] text-slate-500 ml-12">Operations Platform</p>
        </div>

        {/* Mobile sidebar header */}
        <div className="lg:hidden px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-violet-600 flex items-center justify-center">
              <Mountain size={15} className="text-white" />
            </div>
            <span className="text-[16px] font-black tracking-tight bg-gradient-to-r from-sky-400 to-violet-400 bg-clip-text text-transparent">
              NorthStar
            </span>
          </div>
          <button onClick={() => setIsMenuOpen(false)} className="text-slate-500 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors">
            <X size={17} />
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
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all active:scale-[0.97]
                 ${isActive
                   ? 'bg-gradient-to-r from-sky-600 to-sky-500 text-white shadow-md shadow-sky-900/40'
                   : 'text-slate-400 hover:bg-slate-800/80 hover:text-white'}`
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
          <div className="px-1 space-y-1.5">
            <span className={`inline-flex items-center px-3 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${ROLE_COLORS[roleKey] ?? 'bg-slate-700 text-slate-300 border-slate-600'}`}>
              {ROLE_LABELS[roleKey] ?? roleKey}
            </span>
            <p className="text-xs text-slate-400 truncate">
              {user?.store_id ? STORE_MAP[user.store_id] ?? 'Unknown store' : 'All stores · 3 locations'}
            </p>
          </div>
          <button
            onClick={() => { authStore.logout(); navigate('/login') }}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-xl transition-colors border border-transparent hover:border-red-900/40"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 overflow-auto bg-slate-950 relative flex flex-col">
        <div className="flex-1 w-full max-w-full overflow-x-hidden">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
