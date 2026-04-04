import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { WeeklyPoint, TopProduct, Recommendation, Anomaly } from '../api/types'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { Brain, TrendingUp, AlertOctagon, MessageSquare, Send } from 'lucide-react'

const STORE_ID = 'b1000000-0000-0000-0000-000000000001'

export default function ReportsPage() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORE_ID
  const isManager = user?.role !== 'sales_associate'
  const [nlQuery, setNlQuery] = useState('')
  const [nlResult, setNlResult] = useState<any>(null)
  const [nlLoading, setNlLoading] = useState(false)

  const { data: weekly = [] } = useQuery({
    queryKey: ['weekly', storeId],
    queryFn: () => api.get<WeeklyPoint[]>(`/sales/reports/weekly?store_id=${storeId}`),
  })

  const { data: topProducts = [] } = useQuery({
    queryKey: ['top-products', storeId],
    queryFn: () => api.get<TopProduct[]>(`/sales/reports/top-products?store_id=${storeId}`),
  })

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations', storeId],
    queryFn: () => api.get<{ season: string; recommendations: Recommendation[] }>(`/ai/recommendations/${storeId}`),
    enabled: isManager,
  })

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', storeId],
    queryFn: () => api.get<{ anomalies: Anomaly[]; order_count_analyzed: number }>(`/ai/anomalies?store_id=${storeId}`),
    enabled: isManager,
  })

  // Fill in zero-revenue days for last 7 days
  const chartData = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i))
    const dateStr = d.toISOString().split('T')[0]
    const found = weekly.find(w => w.date === dateStr)
    return { day: d.toLocaleDateString('en', { weekday: 'short' }), revenue: found?.revenue ?? 0 }
  })

  async function runNlQuery() {
    if (!nlQuery.trim()) return
    setNlLoading(true)
    try {
      const result = await api.post('/ai/query', { question: nlQuery, store_id: storeId })
      setNlResult(result)
    } catch (e: any) {
      setNlResult({ error: e.message })
    } finally { setNlLoading(false) }
  }

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6">
      <h1 className="text-xl font-bold text-white">Reports & AI Insights</h1>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-sky-400" /> 7-Day Revenue
          </h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                formatter={(v: number) => [`$${v.toFixed(2)}`, 'Revenue']} />
              <Area type="monotone" dataKey="revenue" stroke="#0ea5e9" strokeWidth={2} fill="url(#rev)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Top Products (Units Sold)</h2>
          {topProducts.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-slate-500 text-sm">No sales data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={topProducts.slice(0, 6)} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="product_name" width={120}
                  tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false}
                  tickFormatter={(v: string) => v.length > 14 ? v.slice(0, 14) + '…' : v} />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  formatter={(v: number) => [v, 'Units']} />
                <Bar dataKey="units_sold" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* AI section — manager+ only */}
      {isManager && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Recommendations */}
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
                <Brain size={16} className="text-violet-400" /> AI Recommendations
              </h2>
              {recommendations && (
                <p className="text-xs text-slate-500 mb-3">Season: {recommendations.season}</p>
              )}
              <div className="space-y-2">
                {(recommendations?.recommendations ?? []).map((r, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-900/60 rounded-lg px-3 py-2">
                    <div>
                      <p className="text-sm text-white font-medium">{r.name}</p>
                      <p className="text-xs text-slate-500">{r.category} · ${r.unit_price}</p>
                    </div>
                    <span className="text-xs px-2 py-0.5 bg-violet-900/50 text-violet-300 rounded-full">Push</span>
                  </div>
                ))}
                {!recommendations && <p className="text-sm text-slate-500">Loading…</p>}
              </div>
            </div>

            {/* Anomalies */}
            <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
                <AlertOctagon size={16} className="text-amber-400" /> Anomaly Detection
              </h2>
              {anomalies && (
                <p className="text-xs text-slate-500 mb-3">
                  Analyzed {anomalies.order_count_analyzed} orders · Z-score threshold: 2.5
                </p>
              )}
              {anomalies?.anomalies.length === 0 ? (
                <p className="text-sm text-emerald-400">No anomalies detected</p>
              ) : (
                <div className="space-y-2">
                  {(anomalies?.anomalies ?? []).map((a, i) => (
                    <div key={i} className="bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-red-300 font-medium">{a.reason}</span>
                        <span className="text-slate-500">Z={a.z_score}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Order #{a.order_id.slice(0, 8)} · ${a.total.toFixed(2)} · {a.paid_at.slice(0, 10)}
                      </p>
                    </div>
                  ))}
                  {!anomalies && <p className="text-sm text-slate-500">Loading…</p>}
                </div>
              )}
            </div>
          </div>

          {/* NL Query */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <MessageSquare size={16} className="text-sky-400" /> Ask a Question
            </h2>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={nlQuery} onChange={e => setNlQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && runNlQuery()}
                placeholder="e.g. What are the top selling?"
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
              <button onClick={runNlQuery} disabled={nlLoading}
                className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-1.5 shrink-0">
                <Send size={14} />{nlLoading ? '…' : 'Ask'}
              </button>
            </div>
            {nlResult && (
              <div className="mt-3 bg-slate-900 rounded-lg p-3">
                {nlResult.error ? (
                  <p className="text-red-400 text-sm">{nlResult.error}</p>
                ) : (
                  <>
                    <p className="text-xs text-slate-400 mb-2">
                      Interpreted as: <span className="text-sky-400">{nlResult.interpreted_as}</span>
                      {' '}· {nlResult.row_count} rows
                    </p>
                    <pre className="text-xs text-slate-300 overflow-auto max-h-48 whitespace-pre-wrap">
                      {JSON.stringify(nlResult.results?.slice(0, 10), null, 2)}
                    </pre>
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
