export type Role = 'admin' | 'sales' | 'hr' | 'accountant' | 'technologist' | 'shop_head' | 'storekeeper'

export const ROLE_LABELS: Record<Role, string> = {
  admin: 'Администратор',
  sales: 'Менеджер по продажам',
  hr: 'Отдел кадров',
  accountant: 'Бухгалтерия',
  technologist: 'Технолог',
  shop_head: 'Начальник цеха',
  storekeeper: 'Кладовщик',
}

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  role: Role
  role_display: string
  is_active: boolean
}

export interface Department { id: number; name: string; is_production: boolean; is_active: boolean }
export interface Position { id: number; name: string; base_salary: string }

export interface Employee {
  id: number
  full_name: string
  last_name: string
  first_name: string
  middle_name: string
  birth_date: string | null
  tax_id: string
  phone: string
  address: string
  department: number
  department_name: string
  position: number
  position_name: string
  hire_date: string
  fire_date: string | null
  status: 'active' | 'leave' | 'fired'
}

export type ItemKind = 'raw' | 'product'

export interface Unit { id: number; code: string; name: string }
export interface Category { id: number; name: string; kind: ItemKind; kind_display: string }

export interface Item {
  id: number
  kind: ItemKind
  kind_display: string
  code: string
  name: string
  category: number | null
  category_name: string | null
  unit: number
  unit_code: string
  department: number | null
  department_name: string | null
  shelf_life_days: number
  min_stock: string
  sale_price: string
  is_active: boolean
}

export interface Supplier {
  id: number
  name: string
  tax_id: string
  contact_person: string
  phone: string
  email: string
  address: string
  note: string
  is_active: boolean
}

export type RecipeStatus = 'draft' | 'active' | 'archived'

export interface RecipeLine {
  id?: number
  ingredient: number
  ingredient_name?: string
  unit_code?: string
  quantity: string
  loss_percent: string
}

export interface Recipe {
  id: number
  product: number
  product_name: string
  product_unit: string
  department_name: string | null
  version: number
  status: RecipeStatus
  status_display: string
  output_qty: string
  note: string
  lines: RecipeLine[]
  created_by_name: string | null
  created_at: string
  activated_at: string | null
}

export interface RecipeCalculation {
  qty: string
  lines: { ingredient: number; ingredient_name: string; unit_code: string; quantity: string }[]
}

export type ExpiryStatus = 'ok' | 'expiring' | 'expired'

export interface Lot {
  id: number
  number: string
  item: number
  item_code: string
  item_name: string
  item_kind: ItemKind
  unit_code: string
  supplier: number | null
  supplier_name: string | null
  date: string
  expiry_date: string
  unit_cost: string
  balance: string
  expiry_status: ExpiryStatus
  days_left: number
}

export interface StockRow {
  id: number
  code: string
  name: string
  kind: ItemKind
  unit_code: string
  min_stock: string
  balance: string
  available: string
  expired: string
  below_min: boolean
  nearest_expiry: string | null
}

export interface StockMove {
  id: number
  lot: number
  lot_number: string
  item: number
  item_name: string
  unit_code: string
  kind: string
  kind_display: string
  quantity: string
  reference: string
  created_by_name: string | null
  created_at: string
}

export interface DocLine {
  id?: number
  item: number
  item_name?: string
  unit_code?: string
  quantity: string
  price: string
  amount?: string
}

export interface PurchaseOrderLine extends DocLine { received?: string }

export interface PurchaseOrder {
  id: number
  number: string
  supplier: number
  supplier_name: string
  status: 'draft' | 'sent' | 'partial' | 'received' | 'cancelled'
  status_display: string
  expected_date: string | null
  comment: string
  lines: PurchaseOrderLine[]
  total: string
  created_by_name: string | null
  created_at: string
}

export interface ReceiptLine extends DocLine {
  expiry_date: string | null
  order_line: number | null
  lot: number | null
  lot_number: string | null
}

export interface Receipt {
  id: number
  number: string
  supplier: number
  supplier_name: string
  order: number | null
  order_number: string | null
  date: string
  invoice_number: string
  status: 'draft' | 'posted'
  status_display: string
  comment: string
  lines: ReceiptLine[]
  total: string
  created_by_name: string | null
  posted_by_name: string | null
  posted_at: string | null
}
