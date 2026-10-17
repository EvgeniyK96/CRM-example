import type { Role } from '../api/types'

export interface NavItem { key: string; label: string; roles: Role[] | 'all'; group?: string }

// Администратор видит всё; пустой список ролей — только администратор
export const NAV: NavItem[] = [
  { key: '/', label: 'Главная', roles: 'all' },
  { key: '/orders', label: 'Заказы клиентов', roles: ['sales', 'accountant', 'storekeeper', 'shop_head'], group: 'Продажи' },
  { key: '/clients', label: 'Клиенты', roles: ['sales', 'accountant'], group: 'Продажи' },
  { key: '/tasks', label: 'Задания', roles: ['shop_head', 'technologist', 'storekeeper', 'accountant', 'sales'], group: 'Производство' },
  { key: '/items', label: 'Номенклатура', roles: 'all', group: 'Производство' },
  { key: '/recipes', label: 'Рецептуры', roles: ['technologist', 'shop_head', 'accountant'], group: 'Производство' },
  { key: '/stock', label: 'Остатки', roles: 'all', group: 'Склад' },
  { key: '/shipments', label: 'Отгрузки', roles: ['storekeeper', 'sales', 'accountant'], group: 'Склад' },
  { key: '/moves', label: 'Движения', roles: ['storekeeper', 'accountant', 'shop_head'], group: 'Склад' },
  { key: '/purchase-orders', label: 'Заявки поставщикам', roles: ['storekeeper', 'accountant'], group: 'Закупки' },
  { key: '/receipts', label: 'Приёмки', roles: ['storekeeper', 'accountant'], group: 'Закупки' },
  { key: '/suppliers', label: 'Поставщики', roles: ['storekeeper', 'accountant'], group: 'Закупки' },
  { key: '/invoices', label: 'Счета покупателям', roles: ['accountant', 'sales'], group: 'Бухгалтерия' },
  { key: '/payments', label: 'Платежи', roles: ['accountant', 'sales'], group: 'Бухгалтерия' },
  { key: '/journal', label: 'Журнал операций', roles: ['accountant'], group: 'Бухгалтерия' },
  { key: '/finance', label: 'Финансовые отчёты', roles: ['accountant'], group: 'Бухгалтерия' },
  { key: '/accounts', label: 'План счетов', roles: ['accountant'], group: 'Бухгалтерия' },
  { key: '/employees', label: 'Сотрудники', roles: ['hr', 'accountant', 'shop_head'], group: 'Кадры' },
  { key: '/references', label: 'Справочники', roles: ['technologist', 'hr'], group: 'Настройки' },
  { key: '/users', label: 'Пользователи', roles: [], group: 'Настройки' },
]

export const navRoles = (key: string) => NAV.find((i) => i.key === key)?.roles ?? []
