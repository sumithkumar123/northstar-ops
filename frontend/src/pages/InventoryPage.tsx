import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { InventoryItem } from '../api/types'
import { Search, RefreshCw, AlertTriangle } from 'lucide-react'

const STORE_ID = 'b1000000-0000-0000-0000-000000000001'

function StockBadge({ item }: { item: InventoryItem }) {
  if (item.quantity === 0)
    return <span className="px-2 py-0.5 text-xs rounded-full bg-red-900/60 text-red-300 font-medium">OUT OF STOCK</span>
  if (item.below_reorder)
    return <span className="px-2 py-0.5 text-xs rounded-full bg-amber-900/60 text-amber-300 font-medium">LOW STOCK</span>
  return <span className="px-2 py-0.5 text-xs rounded-full bg-emerald-900/60 text-emerald-300 font-medium">OK</span>
}

function AdjustModal({ item, onClose }: { item: InventoryItem; onClose: () => void }) {
  const [delta, setDelta] = useState('')
  const [type, setType] = useState('restock')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const qc = useQueryClient()
  const storeId = authStore.getUser()?.store_id ?? STORE_ID

  async function submit() {
    setLoading(true); setError('')
    try {
      await api.patch(`/inventory/stores/${storeId}/products/${item.product_id}`, {
        delta: parseInt(delta), transaction_type: type,
      })
      qc.invalidateQueries({ queryKey: ['inventory'] })
      qc.invalidateQueries({ queryKey: ['alerts'] })
      onClose()
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-sm">
        <h3 className="font-semibold text-white mb-1">Adjust Stock</h3>
        <p className="text-xs text-slate-400 mb-4">{item.name} — current: {item.quantity}</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Delta (+ to add, − to remove)</label>
            <input type="number" value={delta} onChange={e => setDelta(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500"
              placeholder="e.g. 10 or -5" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Type</label>
            <select value={type} onChange={e => setType(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white">
              <option value="restock">Restock</option>
              <option value="adjustment">Adjustment</option>
              <option value="transfer_in">Transfer In</option>
              <option value="transfer_out">Transfer Out</option>
            </select>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button onClick={onClose} className="flex-1 px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">Cancel</button>
            <button onClick={submit} disabled={loading || !delta}
              className="flex-1 px-4 py-2 text-sm text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 rounded-lg transition-colors">
              {loading ? 'Saving…' : 'Apply'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function InventoryPage() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORE_ID
  const canEdit = user?.role !== 'sales_associate'
  const [search, setSearch] = useState('')
  const [alertsOnly, setAlertsOnly] = useState(false)
  const [adjusting, setAdjusting] = useState<InventoryItem | null>(null)

  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ['inventory', storeId],
    queryFn: () => api.get<InventoryItem[]>(`/inventory/stores/${storeId}`),
  })

  const filtered = items.filter(i => {
    const matchSearch = i.name.toLowerCase().includes(search.toLowerCase()) || i.sku.toLowerCase().includes(search.toLowerCase())
    return matchSearch && (!alertsOnly || i.below_reorder)
  })

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Inventory</h1>
        <button onClick={() => refetch()} className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors">
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or SKU…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-8 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500" />
        </div>
        <button onClick={() => setAlertsOnly(!alertsOnly)}
          className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors ${
            alertsOnly ? 'bg-amber-900/40 border-amber-700 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
          }`}>
          <AlertTriangle size={14} /> Alerts only
        </button>
      </div>

      {/* Table Wrapper */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px] lg:min-w-full">
            <thead>
              <tr className="border-b border-slate-700 text-left">
                {['SKU', 'Product', 'Qty', 'Reorder At', 'Status', ...(canEdit ? ['Action'] : [])].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Loading…</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No items found</td></tr>
              ) : filtered.map(item => (
              <tr key={item.inventory_id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{item.sku}</td>
                <td className="px-4 py-3 text-white font-medium">{item.name}</td>
                <td className="px-4 py-3">
                  <span className={`font-bold ${item.quantity === 0 ? 'text-red-400' : item.below_reorder ? 'text-amber-400' : 'text-white'}`}>
                    {item.quantity}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">{item.reorder_point}</td>
                <td className="px-4 py-3"><StockBadge item={item} /></td>
                {canEdit && (
                  <td className="px-4 py-3">
                    <button onClick={() => setAdjusting(item)}
                      className="text-xs px-2.5 py-1 bg-slate-700 hover:bg-sky-700 text-slate-300 hover:text-white rounded transition-colors">
                      Adjust
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
          </table>
        </div>
      </div>

      {adjusting && <AdjustModal item={adjusting} onClose={() => setAdjusting(null)} />}
    </div>
  )
}
