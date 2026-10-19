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
  /** Подразделение из карточки сотрудника; у начальника цеха ограничивает доступ к заданиям */
  department: number | null
  department_name: string | null
  /** Производственный цех сотрудника (если есть) */
  production_department: number | null
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
  salary: string
  username: string | null
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

export type ClientKind = 'wholesale' | 'store' | 'brand_store'

export interface Client {
  id: number
  kind: ClientKind
  kind_display: string
  name: string
  tax_id: string
  contact_person: string
  phone: string
  email: string
  legal_address: string
  delivery_address: string
  discount_percent: string
  payment_delay_days: number
  note: string
  is_active: boolean
}

export interface SalesOrderLine extends Omit<DocLine, 'price'> {
  price: string | null
  reserved_qty?: string
  to_produce?: string
}

export type SalesOrderStatus = 'new' | 'confirmed' | 'in_production' | 'ready' | 'shipped' | 'cancelled'

export interface SalesOrder {
  id: number
  number: string
  client: number
  client_name: string
  client_kind: ClientKind
  status: SalesOrderStatus
  status_display: string
  delivery_date: string
  delivery_address: string
  discount_percent: string
  comment: string
  lines: SalesOrderLine[]
  total: string
  created_by_name: string | null
  created_at: string
  confirmed_by_name: string | null
  confirmed_at: string | null
  shipment: number | null
  shipment_number: string | null
}

export interface ShipmentItem {
  id: number
  order_line: number
  item_name: string
  unit_code: string
  lot: number
  lot_number: string
  lot_date: string
  expiry_date: string
  quantity: string
  price: string
  unit_cost: string
}

export interface Shipment {
  id: number
  number: string
  order: number
  order_number: string
  client: number
  client_name: string
  client_tax_id: string
  client_legal_address: string
  delivery_address: string
  payment_delay_days: number
  date: string
  vehicle: string
  driver: string
  comment: string
  items: ShipmentItem[]
  total: string
  cost: string
  created_by_name: string | null
  created_at: string
}

export interface AvailabilityRow {
  line: number
  item: number
  item_name: string
  unit_code: string
  quantity: string
  free_stock: string
  from_stock: string
  to_produce: string
}

export type TaskStatus = 'planned' | 'in_progress' | 'done' | 'cancelled'

export interface TaskAllocation {
  id: number
  order: number
  order_number: string
  order_status: SalesOrderStatus
  client_name: string
  delivery_date: string
  quantity: string
  fulfilled: string
}

export interface ProductionTask {
  id: number
  number: string
  department: number
  department_name: string
  product: number
  product_name: string
  unit_code: string
  recipe: number
  recipe_version: number
  planned_qty: string
  planned_date: string
  status: TaskStatus
  status_display: string
  actual_qty: string | null
  defect_qty: string
  raw_cost: string | null
  unit_cost: string | null
  output_lot: number | null
  output_lot_number: string | null
  comment: string
  allocations: TaskAllocation[]
  created_by_name: string | null
  created_at: string
  started_by_name: string | null
  started_at: string | null
  finished_by_name: string | null
  finished_at: string | null
}

export interface Requirement {
  ingredient: number
  ingredient_name: string
  unit_code: string
  quantity: string
  available: string
  shortage: string
}

export interface TaskConsumption {
  id: number
  lot: number
  lot_number: string
  item_name: string
  unit_code: string
  supplier_name: string | null
  expiry_date: string
  unit_cost: string
  quantity: string
}

export interface DemandGroup {
  product: number
  product_name: string
  unit_code: string
  department: number
  department_name: string | null
  quantity: string
  earliest_date: string
  orders: { order: number; order_number: string; client_name: string; delivery_date: string; quantity: string }[]
}

export interface TraceLot {
  id: number
  number: string
  item_name: string
  unit_code: string
  date: string
  expiry_date: string
  supplier_name: string | null
}

export interface LotTrace {
  lot: TraceLot
  produced_by: { id: number; number: string; department_name: string; recipe_version: number; finished_at: string } | null
  ingredients: (TraceLot & { quantity: string })[]
  used_in: { task: number; task_number: string; quantity: string; output_lot: TraceLot | null }[]
  shipped_to: {
    shipment: number
    shipment_number: string
    date: string
    order: number
    order_number: string
    client_name: string
    quantity: string
  }[]
}

// --- Бухгалтерия ---

export type AccountType = 'asset' | 'liability' | 'equity' | 'income' | 'expense'

export interface Account { id: number; code: string; name: string; type: AccountType; type_display: string; is_active: boolean }

export interface Posting {
  id: number
  debit: number
  debit_code: string
  credit: number
  credit_code: string
  amount: string
  client: number | null
  client_name: string | null
  supplier: number | null
  supplier_name: string | null
  comment: string
}

export interface JournalEntry {
  id: number
  date: string
  description: string
  source_type: string
  source_display: string
  source_id: number | null
  postings: Posting[]
  total: string
  created_by_name: string | null
  created_at: string
}

export interface Invoice {
  id: number
  number: string
  client: number
  client_name: string
  shipment: number | null
  shipment_number: string | null
  order: number | null
  order_number: string | null
  date: string
  due_date: string
  amount: string
  paid: string
  remaining: string
  status: 'unpaid' | 'partial' | 'paid'
  days_overdue: number
}

export interface Payment {
  id: number
  number: string
  direction: 'incoming' | 'outgoing'
  direction_display: string
  method: 'bank' | 'cash'
  method_display: string
  date: string
  amount: string
  client: number | null
  client_name: string | null
  supplier: number | null
  supplier_name: string | null
  invoice: number | null
  invoice_number: string | null
  comment: string
  allocations: { invoice: number; invoice_number: string; amount: string }[]
  created_by_name: string | null
  created_at: string
}

export interface TrialBalanceRow {
  account: number
  code: string
  name: string
  opening_debit: string
  opening_credit: string
  turnover_debit: string
  turnover_credit: string
  closing_debit: string
  closing_credit: string
}

export interface TrialBalance {
  date_from: string
  date_to: string
  rows: TrialBalanceRow[]
  totals: Partial<Record<keyof Omit<TrialBalanceRow, 'account' | 'code' | 'name'>, string>>
}

export interface AccountCard {
  account: string
  name: string
  opening: string
  closing: string
  rows: {
    date: string
    entry: number
    description: string
    source_type: string
    source_id: number | null
    corr_account: string
    debit: string | null
    credit: string | null
    counterparty: string | null
    balance: string
  }[]
}

export interface Receivables {
  rows: { client: number; client_name: string; invoiced: string; paid: string; debt: string; advance: string; overdue: string; open_invoices: number }[]
  total_debt: string
  total_overdue: string
}

export interface Payables {
  rows: { supplier: number; supplier_name: string; received: string; paid: string; debt: string }[]
  total_debt: string
}

export interface ProfitLoss {
  date_from: string
  date_to: string
  revenue: string
  cost_of_sales: string
  gross_profit: string
  gross_margin: string | null
  admin_expenses: string
  other_expenses: string
  net_profit: string
}

// --- Кадры и зарплата ---

export interface HROrder {
  id: number
  number: string
  kind: 'hire' | 'transfer' | 'salary' | 'dismissal'
  kind_display: string
  employee: number
  employee_name: string
  date: string
  from_department_name: string | null
  to_department_name: string | null
  from_position_name: string | null
  to_position_name: string | null
  from_salary: string | null
  to_salary: string | null
  reason: string
  created_by_name: string | null
  created_at: string
}

export interface Absence {
  id: number
  employee: number
  employee_name: string
  department_name: string
  kind: 'vacation' | 'sick' | 'business_trip' | 'unpaid'
  kind_display: string
  date_from: string
  date_to: string
  days: number
  comment: string
}

export interface Holiday { id: number; date: string; name: string }

export interface Timesheet {
  year: number
  month: number
  norm_days: number
  days: { day: number; weekday: number; workday: boolean; holiday: boolean }[]
  rows: {
    employee: number
    full_name: string
    department_name: string
    position_name: string
    cells: string[]
    worked_days: number
    vacation_days: number
    sick_days: number
    unpaid_days: number
  }[]
}

export interface PayrollRate {
  id: number
  code: string
  name: string
  payer: 'employee' | 'employer'
  payer_display: string
  base: 'gross' | 'taxable'
  base_display: string
  percent: string
  account_code: string
  is_active: boolean
}

export interface PayrollPeriod {
  id: number
  year: number
  month: number
  status: 'draft' | 'posted' | 'paid'
  status_display: string
  calculated_at: string | null
  posted_at: string | null
  paid_at: string | null
  totals: { employees: number; gross: string; withheld: string; net: string; employer_total: string }
}

export interface Payslip {
  id: number
  period: number
  period_label: string
  period_status: PayrollPeriod['status']
  employee: number
  employee_name: string
  department: number
  department_name: string
  position_name: string
  salary: string
  norm_days: number
  worked_days: number
  vacation_days: number
  sick_days: number
  unpaid_days: number
  salary_accrued: string
  vacation_pay: string
  sick_pay: string
  bonus: string
  gross: string
  withheld: string
  net: string
  employer_total: string
  lines: { id: number; code: string; name: string; payer: 'employee' | 'employer'; base: string; percent: string; amount: string }[]
}

// --- Отчёты ---

export interface ProductSales { product: number; name: string; unit_code: string; quantity: string; revenue: string; cost: string; margin: string; margin_percent: string | null }
export interface ClientSales { client: number; name: string; kind: ClientKind; revenue: string; cost: string; margin: string; margin_percent: string | null }
export interface WorkshopLoad { department: number; name: string; planned: number; in_progress: number; done: number }
export interface ProductionOutput { product: number; name: string; unit_code: string; department_name: string; tasks: number; output: string; defect: string; raw_cost: string; defect_percent: string }
export interface BelowMin { item: number; code: string; name: string; unit_code: string; available: string; min_stock: string; shortage: string }
export interface ExpiringLot { lot: number; number: string; name: string; kind: ItemKind; unit_code: string; balance: string; expiry_date: string; days_left: number; status: 'expiring' | 'expired'; value: string }
export interface StockValuation { item: number; code: string; name: string; kind: ItemKind; unit_code: string; quantity: string; available: string; value: string; min_stock: string }

export interface SalesReport {
  revenue: string
  cost: string
  gross_profit: string
  by_day: { date: string; revenue: string }[]
  by_product: ProductSales[]
  by_client: ClientSales[]
}

export interface ProductionReport { load: WorkshopLoad[]; output: ProductionOutput[] }

export interface StockReport {
  raw_value: string
  product_value: string
  expired_value: string
  valuation: StockValuation[]
  expiring: ExpiringLot[]
  below_min: BelowMin[]
}

export interface Dashboard {
  date_from: string
  date_to: string
  sections: ('sales' | 'finance' | 'production' | 'warehouse')[]
  sales?: {
    revenue: string
    revenue_prev: string
    gross_profit: string
    by_day: { date: string; revenue: string }[]
    top_products: ProductSales[]
    top_clients: ClientSales[]
    orders: Record<SalesOrderStatus, number>
  }
  finance?: { receivables: string; overdue: string }
  production?: ProductionReport
  warehouse?: Pick<StockReport, 'raw_value' | 'product_value' | 'expired_value' | 'below_min' | 'expiring'>
}

/** Запись живой ленты / таймлайна документа */
export interface Activity {
  id: number
  kind: 'created' | 'status' | 'comment' | 'post'
  kind_display: string
  text: string
  author: number | null
  author_name: string | null
  author_role: string | null
  old_status: string
  new_status: string
  created_at: string
  target: { type: string; id: number; title: string; path: string | null } | null
  can_delete: boolean
}
