import type { Role } from '../api/types'

export interface NavItem { key: string; label: string; roles: Role[] | 'all' }

// Администратор видит всё; пустой список ролей — только администратор
export const NAV: NavItem[] = [
  { key: '/', label: 'Главная', roles: 'all' },
  { key: '/items', label: 'Номенклатура', roles: 'all' },
  { key: '/recipes', label: 'Рецептуры', roles: ['technologist', 'shop_head', 'accountant'] },
  { key: '/suppliers', label: 'Поставщики', roles: ['storekeeper', 'accountant'] },
  { key: '/employees', label: 'Сотрудники', roles: ['hr', 'accountant', 'shop_head'] },
  { key: '/references', label: 'Справочники', roles: ['technologist', 'hr'] },
  { key: '/users', label: 'Пользователи', roles: [] },
]

export const navRoles = (key: string) => NAV.find((i) => i.key === key)?.roles ?? []
