import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { DailyReport, WeeklyPoint, InventoryItem } from '../api/types'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { DollarSign, ShoppingBag, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { STORE_MAP } from '../components/Layout'

const TODAY = new Date().toISOString().split('T')[0]

const STORES = [
  { id: 'b1000000-0000-0000-0000-000000000001', name: 'NYC Flagship' },
  { id: 'b1000000-0000-0000-0000-000000000002', name: 'Boston Outlet' },
  { id: 'b1000000-0000-0000-0000-000000000003', name: 'London Central' },
]

function Trend({ value, suffix = '' }: { value: number | null; suffix?: string }) {
  if (value === null) return null
  if (value > 0) return (
    <span className="flex items-center gap-0.5 text-emerald-400 text-xs font-medium">
      <TrendingUp size={12} /> +{value}{suffix}
    </span>
  )
  if (value < 0) return (
    <span className="flex items-center gap-0.5 text-red-400 text-xs font-medium">
      <TrendingDown size={12} /> {value}{suffix}
    </span>
  )
  return (
    <span className="flex items-center gap-0.5 text-slate-500 text-xs font-medium">
      <Minus size={12} /> No change
    </span>
  )
}

function KPICard({ label, value, sub, icon: Icon, color, trend, trendSuffix }: {
  label: string; value: string; sub?: string; icon: React.ElementType; color: string
  trend?: number | null; trendSuffix?: string
}) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-slate-600 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={16} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <div className="flex items-center justify-between mt-1.5">
        {sub && <p className="text-xs text-slate-500">{sub}</p>}
        {trend !== undefined && <Trend value={trend ?? null} suffix={trendSuffix} />}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORES[0].id

  const { data: daily } = useQuery({
    queryKey: ['daily', storeId],
    queryFn: () => api.get<DailyReport>(`/sales/reports/daily?store_id=${storeId}&report_date=${TODAY}`),
  })

  const { data: weekly = [] } = useQuery({
    queryKey: ['weekly', storeId],
    queryFn: () => api.get<WeeklyPoint[]>(`/sales/reports/weekly?store_id=${storeId}`),
  })

  const { data: alerts = [] } = useQuery({
    queryKey: ['alerts', storeId],
    queryFn: () => api.get<InventoryItem[]>(`/inventory/stores/${storeId}/alerts`),
  })

  // Fill in zero-revenue days for last 7 days
  const chartData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().split('T')[0]
    const found = weekly.find(w => w.date === dateStr)
    return { day: d.toLocaleDateString('en', { weekday: 'short' }), revenue: found?.revenue ?? 0 }
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {STORE_MAP[storeId] ?? storeId} · {new Date().toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          label="Today's Revenue"
          value={daily ? `$${daily.revenue.toFixed(2)}` : '—'}
          sub="paid orders"
          icon={DollarSign}
          color="bg-sky-600"
          trend={daily ? (daily.revenue > 0 ? weekly.length : 0) : null}
          trendSuffix=" days active"
        />
        <KPICard
          label="Orders Today"
          value={daily ? String(daily.order_count) : '—'}
          sub="completed"
          icon={ShoppingBag}
          color="bg-emerald-600"
          trend={daily ? daily.order_count : null}
          trendSuffix=" orders"
        />
        <KPICard
          label="Low Stock Items"
          value={String(alerts.length)}
          sub={alerts.filter(a => a.severity === 'critical').length + ' critical'}
          icon={AlertTriangle}
          color={alerts.length > 0 ? 'bg-amber-600' : 'bg-slate-600'}
          trend={alerts.length > 0 ? -alerts.length : 0}
          trendSuffix=" items"
        />
        <KPICard
          label="Tax Collected"
          value={daily ? `$${daily.tax_collected.toFixed(2)}` : '—'}
          sub="today"
          icon={TrendingUp}
          color="bg-violet-600"
          trend={daily ? (daily.tax_collected > 0 ? 8 : 0) : null}
          trendSuffix="% rate"
        />
      </div>

      {/* Revenue Chart */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-4">7-Day Revenue Trend</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={(v: number) => [`$${v.toFixed(2)}`, 'Revenue']}
            />
            <Bar dataKey="revenue" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Low stock alerts */}
      {alerts.length > 0 && (
        <div className="mt-4 bg-amber-900/20 border border-amber-700/50 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-amber-300 mb-2 flex items-center gap-2">
            <AlertTriangle size={16} /> Low Stock Alerts
          </h3>
          <div className="space-y-1.5">
            {alerts.slice(0, 5).map(item => (
              <div key={item.inventory_id} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">{item.name} <span className="text-slate-500">({item.sku})</span></span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  item.severity === 'critical' ? 'bg-red-900/60 text-red-300' : 'bg-amber-900/60 text-amber-300'
                }`}>
                  {item.quantity} left
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
