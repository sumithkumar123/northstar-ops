export interface InventoryItem {
  inventory_id: string
  product_id: string
  sku: string
  name: string
  quantity: number
  unit_price: number
  reorder_point: number
  below_reorder: boolean
  severity?: 'critical' | 'warning'
  last_updated: string
}

export interface DailyReport {
  store_id: string
  date: string
  order_count: number
  revenue: number
  tax_collected: number
}

export interface WeeklyPoint { date: string; revenue: number; order_count: number }
export interface TopProduct  { sku: string; product_name: string; units_sold: number; revenue: number }

export interface OrderItem {
  product_id: string; sku: string; product_name: string
  quantity: number; unit_price: number; line_total: number
}

export interface Order {
  id: string; store_id: string; cashier_id: string; status: string
  subtotal: number; tax_amount: number; total: number
  payment_method: string; paid_at: string | null; items: OrderItem[]
}

export interface Recommendation {
  product_id: string; sku: string; name: string
  category: string; unit_price: number; reason: string
}

export interface Anomaly {
  order_id: string; total: number; cashier_id: string
  paid_at: string; z_score: number; reason: string
}
