import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { InventoryItem, Order } from '../api/types'
import { ShoppingCart, Plus, Minus, Trash2, CheckCircle, AlertCircle, ChevronUp, ChevronDown } from 'lucide-react'

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
  const [cart, setCart]             = useState<CartItem[]>([])
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [loading, setLoading]       = useState(false)
  const [toast, setToast]           = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [search, setSearch]         = useState('')
  const [cartOpen, setCartOpen]     = useState(false)   // mobile cart expanded state
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
        if (existing.cartQty >= item.quantity) return prev
        return prev.map(c => c.product_id === item.product_id ? { ...c, cartQty: c.cartQty + 1 } : c)
      }
      return [...prev, { ...item, cartQty: 1 }]
    })
    // Auto-open the cart on mobile when first item is added
    setCartOpen(true)
  }

  function updateQty(productId: string, delta: number) {
    setCart(prev => prev
      .map(c => c.product_id === productId ? { ...c, cartQty: c.cartQty + delta } : c)
      .filter(c => c.cartQty > 0)
    )
  }

  const subtotal   = cart.reduce((s, i) => s + i.unit_price * i.cartQty, 0)
  const tax        = subtotal * TAX_RATE
  const total      = subtotal + tax
  const itemCount  = cart.reduce((s, i) => s + i.cartQty, 0)

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
      setCartOpen(false)
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
    /* ── Desktop: side-by-side │ Mobile: products + sticky bottom cart ── */
    <div className="flex flex-col lg:flex-row h-full overflow-hidden bg-slate-950">

      {/* ── Products panel ───────────────────────────────────────────── */}
      <div className={`flex-1 p-4 sm:p-6 overflow-auto border-b lg:border-b-0 lg:border-r border-slate-800 ${
        /* On mobile give extra bottom padding so the sticky cart bar doesn't cover last product */
        'pb-24 lg:pb-6'
      }`}>
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-white">Point of Sale</h1>
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <span className="absolute inset-y-0 left-3 flex items-center text-slate-500">
            <ShoppingCart size={14} />
          </span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search products…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>

        {/* Product grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(item => (
            <button
              key={item.product_id}
              onClick={() => addToCart(item)}
              disabled={item.quantity === 0}
              className="bg-slate-800 border border-slate-700 hover:border-sky-600 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl p-4 text-left transition-all hover:shadow-lg hover:shadow-sky-900/20 active:scale-[0.98] group relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-2">
                <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded font-bold ${
                  item.quantity === 0 ? 'bg-red-900/50 text-red-300' :
                  item.below_reorder ? 'bg-amber-900/50 text-amber-300' :
                  'bg-slate-700 text-slate-400'
                }`}>
                  {item.quantity === 0 ? 'Out of Stock' : `${item.quantity} In Stock`}
                </span>
                <Plus size={14} className="text-slate-600 group-hover:text-sky-400 transition-colors" />
              </div>
              <p className="text-sm font-semibold text-white leading-tight mb-0.5 truncate">{item.name}</p>
              <p className="text-[10px] text-slate-500 mb-2 font-mono uppercase">{item.sku}</p>
              <p className="text-lg font-bold text-sky-400">${item.unit_price.toFixed(2)}</p>
              <div className="absolute inset-0 bg-sky-600/10 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            </button>
          ))}
        </div>
      </div>

      {/* ── Desktop Cart Panel ────────────────────────────────────────── */}
      <div className="hidden lg:flex w-80 xl:w-96 shrink-0 bg-slate-900/50 flex-col h-full border-slate-800">
        {/* Cart header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/80">
          <ShoppingCart size={16} className="text-sky-400" />
          <span className="font-semibold text-white text-sm">Cart</span>
          <span className="ml-auto text-xs bg-sky-600/20 text-sky-400 px-2 py-0.5 rounded-full font-bold border border-sky-600/30">
            {itemCount} items
          </span>
        </div>

        {/* Cart items */}
        <div className="flex-1 overflow-auto px-4 py-3 space-y-2">
          {cart.length === 0 ? (
            <div className="text-center py-10">
              <ShoppingCart size={24} className="text-slate-700 mx-auto mb-2" />
              <p className="text-slate-600 text-sm">Cart is empty</p>
              <p className="text-slate-700 text-xs mt-1">Tap a product to add</p>
            </div>
          ) : cart.map(item => (
            <div key={item.product_id} className="bg-slate-800 rounded-xl p-3">
              <div className="flex items-start justify-between mb-2">
                <p className="text-sm text-white font-medium leading-tight pr-1">{item.name}</p>
                <button onClick={() => setCart(c => c.filter(i => i.product_id !== item.product_id))} className="text-slate-600 hover:text-red-400 shrink-0">
                  <Trash2 size={12} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button onClick={() => updateQty(item.product_id, -1)} className="w-6 h-6 flex items-center justify-center bg-slate-700 hover:bg-slate-600 rounded-lg text-white">
                    <Minus size={10} />
                  </button>
                  <span className="text-sm text-white w-5 text-center font-medium">{item.cartQty}</span>
                  <button onClick={() => updateQty(item.product_id, 1)} disabled={item.cartQty >= item.quantity} className="w-6 h-6 flex items-center justify-center bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded-lg text-white">
                    <Plus size={10} />
                  </button>
                </div>
                <span className="text-sm font-semibold text-white">${(item.unit_price * item.cartQty).toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <div className="px-4 py-4 border-t border-slate-800 space-y-3 bg-slate-900/60">
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between text-slate-400">
              <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Tax (8%)</span><span>${tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-bold text-white text-base pt-1.5 border-t border-slate-700">
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
            className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white font-semibold rounded-xl py-2.5 text-sm transition-all active:scale-[0.98]">
            {loading ? 'Processing…' : `Charge $${total.toFixed(2)}`}
          </button>
        </div>
      </div>

      {/* ── Mobile Sticky Cart Bar + Sheet ───────────────────────────── */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40">
        {/* Cart Sheet (slides up when open) */}
        <div className={`transition-all duration-300 ease-in-out ${
          cartOpen ? 'max-h-[70vh]' : 'max-h-0'
        } overflow-hidden bg-slate-900 border-t border-slate-700`}>
          <div className="px-4 py-3 space-y-2 overflow-auto max-h-[55vh]">
            {cart.length === 0 ? (
              <p className="text-center text-slate-600 text-sm py-4">Add products to your cart</p>
            ) : cart.map(item => (
              <div key={item.product_id} className="bg-slate-800 rounded-xl p-3 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{item.name}</p>
                  <p className="text-xs text-sky-400 font-bold">${item.unit_price.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => updateQty(item.product_id, -1)} className="w-7 h-7 flex items-center justify-center bg-slate-700 hover:bg-slate-600 rounded-lg text-white">
                    <Minus size={11} />
                  </button>
                  <span className="text-sm text-white w-5 text-center font-bold">{item.cartQty}</span>
                  <button onClick={() => updateQty(item.product_id, 1)} disabled={item.cartQty >= item.quantity} className="w-7 h-7 flex items-center justify-center bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded-lg text-white">
                    <Plus size={11} />
                  </button>
                  <button onClick={() => setCart(c => c.filter(i => i.product_id !== item.product_id))} className="w-7 h-7 flex items-center justify-center text-slate-600 hover:text-red-400">
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}

            {/* Totals + checkout */}
            {cart.length > 0 && (
              <div className="pt-2 space-y-2.5">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Tax (8%)</span><span>${tax.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm font-bold text-white border-t border-slate-700 pt-2">
                  <span>Total</span><span>${total.toFixed(2)}</span>
                </div>
                <select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white">
                  <option value="card">Card</option>
                  <option value="cash">Cash</option>
                  <option value="mobile_pay">Mobile Pay</option>
                </select>
                <button onClick={checkout} disabled={loading}
                  className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold rounded-xl py-3 text-sm transition-all active:scale-[0.98]">
                  {loading ? 'Processing…' : `Charge $${total.toFixed(2)}`}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Sticky Cart Tab Bar */}
        <button
          onClick={() => setCartOpen(o => !o)}
          className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors ${
            itemCount > 0
              ? 'bg-sky-600 hover:bg-sky-500'
              : 'bg-slate-900 border-t border-slate-800'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <ShoppingCart size={18} className={itemCount > 0 ? 'text-white' : 'text-slate-500'} />
            <span className={`font-semibold text-sm ${itemCount > 0 ? 'text-white' : 'text-slate-500'}`}>
              {itemCount > 0 ? `${itemCount} item${itemCount !== 1 ? 's' : ''} in cart` : 'Cart'}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {itemCount > 0 && (
              <span className="font-bold text-white text-sm">${total.toFixed(2)}</span>
            )}
            {cartOpen
              ? <ChevronDown size={18} className={itemCount > 0 ? 'text-white' : 'text-slate-600'} />
              : <ChevronUp   size={18} className={itemCount > 0 ? 'text-white' : 'text-slate-600'} />
            }
          </div>
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-20 lg:bottom-6 right-4 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium z-50 ${
          toast.type === 'success' ? 'bg-emerald-700 text-white' : 'bg-red-700 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
          {toast.msg}
        </div>
      )}
    </div>
  )
}
