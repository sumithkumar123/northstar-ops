import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { InventoryItem, Order } from '../api/types'
import { ShoppingCart, Plus, Minus, Trash2, CheckCircle, AlertCircle } from 'lucide-react'

const STORE_ID = 'b1000000-0000-0000-0000-000000000001'
const TAX_RATE = 0.08

interface CartItem extends InventoryItem { cartQty: number }

function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16)
  })
}

export default function POSPage() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORE_ID
  const [cart, setCart] = useState<CartItem[]>([])
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [search, setSearch] = useState('')
  const qc = useQueryClient()

  const { data: products = [] } = useQuery({
    queryKey: ['inventory', storeId],
    queryFn: () => api.get<InventoryItem[]>(`/inventory/stores/${storeId}`),
  })

  const filtered = products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) || p.sku.toLowerCase().includes(search.toLowerCase())
  )

  function addToCart(item: InventoryItem) {
    setCart(prev => {
      const existing = prev.find(c => c.product_id === item.product_id)
      if (existing) {
        if (existing.cartQty >= item.quantity) return prev  // don't exceed stock
        return prev.map(c => c.product_id === item.product_id ? { ...c, cartQty: c.cartQty + 1 } : c)
      }
      return [...prev, { ...item, cartQty: 1 }]
    })
  }

  function updateQty(productId: string, delta: number) {
    setCart(prev => prev
      .map(c => c.product_id === productId ? { ...c, cartQty: c.cartQty + delta } : c)
      .filter(c => c.cartQty > 0)
    )
  }

  const subtotal = cart.reduce((s, i) => s + i.unit_price * i.cartQty, 0)
  const tax      = subtotal * TAX_RATE
  const total    = subtotal + tax

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 4000)
  }

  async function checkout() {
    if (cart.length === 0) return
    setLoading(true)
    try {
      const order = await api.post<Order>('/sales/orders', {
        store_id: storeId,
        payment_method: paymentMethod,
        country_code: 'US',
        state_code: 'NY',
        offline_id: uuid(),
        items: cart.map(c => ({
          product_id: c.product_id,
          sku: c.sku,
          product_name: c.name,
          quantity: c.cartQty,
          unit_price: c.unit_price,
        })),
      })
      setCart([])
      qc.invalidateQueries({ queryKey: ['inventory'] })
      qc.invalidateQueries({ queryKey: ['daily'] })
      showToast('success', `Order #${order.id.slice(0, 8)} — $${order.total.toFixed(2)} paid`)
    } catch (e: any) {
      showToast('error', e.message || 'Checkout failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full">
      {/* Products panel */}
      <div className="flex-1 p-6 overflow-auto border-r border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-white">Point of Sale</h1>
        </div>
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search products…"
          className="w-full mb-4 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
        />
        <div className="grid grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(item => (
            <button
              key={item.product_id}
              onClick={() => addToCart(item)}
              disabled={item.quantity === 0}
              className="bg-slate-800 border border-slate-700 hover:border-sky-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl p-4 text-left transition-all hover:shadow-lg hover:shadow-sky-900/20 group"
            >
              <div className="flex items-start justify-between mb-2">
                <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                  item.quantity === 0 ? 'bg-red-900/50 text-red-300' :
                  item.below_reorder ? 'bg-amber-900/50 text-amber-300' :
                  'bg-slate-700 text-slate-400'
                }`}>
                  {item.quantity === 0 ? 'Out' : `${item.quantity} left`}
                </span>
                <Plus size={14} className="text-slate-600 group-hover:text-sky-400 transition-colors" />
              </div>
              <p className="text-sm font-medium text-white leading-tight mb-1">{item.name}</p>
              <p className="text-xs text-slate-500 mb-2">{item.sku}</p>
              <p className="text-base font-bold text-sky-400">${item.unit_price.toFixed(2)}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Cart panel */}
      <div className="w-80 shrink-0 bg-slate-900 flex flex-col">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2">
          <ShoppingCart size={18} className="text-sky-400" />
          <span className="font-semibold text-white">Cart</span>
          <span className="ml-auto text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">{cart.length} items</span>
        </div>

        <div className="flex-1 overflow-auto px-4 py-3 space-y-2">
          {cart.length === 0 ? (
            <p className="text-center text-slate-600 text-sm py-8">Cart is empty</p>
          ) : cart.map(item => (
            <div key={item.product_id} className="bg-slate-800 rounded-lg p-3">
              <div className="flex items-start justify-between mb-2">
                <p className="text-sm text-white font-medium leading-tight">{item.name}</p>
                <button onClick={() => setCart(c => c.filter(i => i.product_id !== item.product_id))} className="text-slate-600 hover:text-red-400 ml-1 shrink-0">
                  <Trash2 size={12} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button onClick={() => updateQty(item.product_id, -1)} className="w-6 h-6 flex items-center justify-center bg-slate-700 hover:bg-slate-600 rounded text-white text-xs">
                    <Minus size={10} />
                  </button>
                  <span className="text-sm text-white w-5 text-center">{item.cartQty}</span>
                  <button onClick={() => updateQty(item.product_id, 1)} disabled={item.cartQty >= item.quantity} className="w-6 h-6 flex items-center justify-center bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded text-white text-xs">
                    <Plus size={10} />
                  </button>
                </div>
                <span className="text-sm font-semibold text-white">${(item.unit_price * item.cartQty).toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <div className="px-5 py-4 border-t border-slate-800 space-y-3">
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Tax (8%)</span><span>${tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-bold text-white text-base pt-1 border-t border-slate-700">
              <span>Total</span><span>${total.toFixed(2)}</span>
            </div>
          </div>

          <select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
            <option value="card">Card</option>
            <option value="cash">Cash</option>
            <option value="mobile_pay">Mobile Pay</option>
          </select>

          <button onClick={checkout} disabled={cart.length === 0 || loading}
            className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white font-semibold rounded-lg py-2.5 text-sm transition-colors">
            {loading ? 'Processing…' : `Charge $${total.toFixed(2)}`}
          </button>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium z-50 ${
          toast.type === 'success' ? 'bg-emerald-700 text-white' : 'bg-red-700 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {toast.msg}
        </div>
      )}
    </div>
  )
}
