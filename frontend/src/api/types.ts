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
