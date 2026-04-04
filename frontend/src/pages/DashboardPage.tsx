import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { DailyReport, WeeklyPoint, InventoryItem } from '../api/types'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import {
  DollarSign,
  ShoppingBag,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Bot,
  ShieldCheck,
  Radar,
} from 'lucide-react'
import { STORE_MAP } from '../components/Layout'
import AgentActivityFeed from '../components/AgentActivityFeed'

const TODAY = new Date().toISOString().split('T')[0]

const STORES = [
  { id: 'b1000000-0000-0000-0000-000000000001', name: 'NYC Flagship' },
  { id: 'b1000000-0000-0000-0000-000000000002', name: 'Boston Outlet' },
  { id: 'b1000000-0000-0000-0000-000000000003', name: 'London Central' },
]

function Trend({ value, suffix = '' }: { value: number | null; suffix?: string }) {
  if (value === null) return null
  if (value > 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-emerald-300">
        <TrendingUp size={12} /> +{value}{suffix}
      </span>
    )
  }
  if (value < 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-rose-300">
        <TrendingDown size={12} /> {value}{suffix}
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-slate-500">
      <Minus size={12} /> Stable
    </span>
  )
}

function KPICard({ label, value, sub, icon: Icon, color, trend, trendSuffix }: {
  label: string
  value: string
  sub?: string
  icon: React.ElementType
  color: string
  trend?: number | null
  trendSuffix?: string
}) {
  return (
    <div className="rounded-[24px] border border-slate-800 bg-slate-900/75 p-5 shadow-xl shadow-slate-950/40">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-500">{label}</span>
        <div className={`rounded-2xl p-2 ${color}`}>
          <Icon size={16} className="text-white" />
        </div>
      </div>
      <p className="text-3xl font-semibold text-white">{value}</p>
      <div className="mt-2 flex items-center justify-between gap-3">
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

  const chartData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().split('T')[0]
    const found = weekly.find(w => w.date === dateStr)
    return { day: d.toLocaleDateString('en', { weekday: 'short' }), revenue: found?.revenue ?? 0 }
  })

  const storeName = STORE_MAP[storeId] ?? storeId
  const commandSummary = alerts.length > 0
    ? `${alerts.length} products need attention. The agent can prioritize restock or transfer actions for you.`
    : 'Inventory is currently healthy. Use the agent to check transfers, anomalies, and performance without opening multiple reports.'
  const heroSummary = alerts.length > 0
    ? `Track sales, low-stock risk, transfers, and anomaly checks for ${storeName}. ${alerts.length} products currently need manager attention.`
    : `Track sales, inventory health, transfers, and anomaly checks for ${storeName} from one operational control room.`

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.45fr)_420px]">
        <div className="space-y-6">
          <section className="relative overflow-hidden rounded-[32px] border border-cyan-500/20 bg-[linear-gradient(135deg,rgba(14,116,144,0.24),rgba(15,23,42,0.92)_45%,rgba(30,41,59,0.96))] p-6 shadow-2xl shadow-cyan-950/20">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(59,130,246,0.14),transparent_32%)]" />
            <div className="relative space-y-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-2xl">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-300/80">
                    Store Command Center
                  </p>
                  <h1 className="display-font mt-2 text-3xl leading-tight text-white sm:text-4xl">
                    {storeName} Operations Hub
                  </h1>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                    {heroSummary}
                  </p>
                </div>
                <div className="grid min-w-[230px] gap-3 sm:grid-cols-3 lg:grid-cols-1">
                  <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                      <Bot size={12} className="text-cyan-300" />
                      Store Agent
                    </div>
                    <p className="mt-2 text-sm font-semibold text-white">Answers questions using live {storeName} data</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                      <Radar size={12} className="text-violet-300" />
                      Background Scans
                    </div>
                    <p className="mt-2 text-sm font-semibold text-white">Checks {storeName} every 5-10 minutes</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-slate-400">
                      <ShieldCheck size={12} className="text-emerald-300" />
                      Audit Trail
                    </div>
                    <p className="mt-2 text-sm font-semibold text-white">Logs every recommendation and alert</p>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-white/10 bg-slate-950/40 px-4 py-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Current Store Snapshot
                </p>
                <p className="mt-2 text-sm leading-7 text-slate-200">{commandSummary}</p>
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <KPICard
              label="Today's Revenue"
              value={daily ? `$${daily.revenue.toFixed(2)}` : '—'}
              sub="paid orders"
              icon={DollarSign}
              color="bg-cyan-600"
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
              sub={`${alerts.filter(a => a.severity === 'critical').length} critical`}
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

          <div className="rounded-[28px] border border-slate-800 bg-slate-900/75 p-5 shadow-xl shadow-slate-950/40">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-500">
                  Revenue
                </p>
                <h2 className="display-font text-2xl text-white">7-Day Demand Pulse</h2>
              </div>
              <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[11px] text-cyan-300">
                Live weekly report
              </span>
            </div>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(34,211,238,0.08)' }}
                  contentStyle={{
                    backgroundColor: '#020617',
                    border: '1px solid #1e293b',
                    borderRadius: 16,
                    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                  }}
                  labelStyle={{ color: '#94a3b8', fontWeight: 600, fontSize: 12 }}
                  itemStyle={{ color: '#67e8f9' }}
                  formatter={(v: number) => [`$${v.toFixed(2)}`, 'Revenue']}
                />
                <Bar dataKey="revenue" fill="#22d3ee" radius={[8, 8, 0, 0]} activeBar={{ fill: '#67e8f9' }} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-[28px] border border-slate-800 bg-slate-900/75 p-5 shadow-xl shadow-slate-950/40">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-500">
                  Inventory
                </p>
                <h2 className="display-font text-2xl text-white">Operational Watchlist</h2>
              </div>
              <span className={`rounded-full px-3 py-1 text-[11px] font-medium ${
                alerts.length > 0
                  ? 'border border-amber-500/20 bg-amber-500/10 text-amber-300'
                  : 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
              }`}>
                {alerts.length > 0 ? 'Needs manager review' : 'Healthy inventory'}
              </span>
            </div>

            {alerts.length > 0 ? (
              <div className="space-y-2">
                {alerts.slice(0, 6).map(item => (
                  <div
                    key={item.inventory_id}
                    className="flex items-center justify-between rounded-2xl border border-amber-500/15 bg-amber-500/5 px-4 py-3 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-white">{item.name}</p>
                      <p className="text-xs text-slate-500">{item.sku}</p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                      item.severity === 'critical'
                        ? 'bg-rose-500/15 text-rose-300'
                        : 'bg-amber-500/15 text-amber-300'
                    }`}>
                      {item.quantity} left
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-[24px] border border-emerald-500/20 bg-emerald-500/5 px-4 py-6 text-center">
                <p className="text-lg font-semibold text-emerald-300">All products in stock</p>
                <p className="mt-2 text-sm text-slate-500">
                  No items are below reorder point right now. Ask the agent about transfers or weekend demand to plan ahead.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="xl:sticky xl:top-6">
          <AgentActivityFeed />
        </div>
      </div>
    </div>
  )
}
