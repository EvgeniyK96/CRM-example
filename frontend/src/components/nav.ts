import {
  AppstoreOutlined, BarChartOutlined, BookOutlined, CalendarOutlined, CarOutlined, DollarOutlined, ExperimentOutlined,
  FieldTimeOutlined, FileDoneOutlined, FileTextOutlined, FundOutlined, HomeOutlined, MessageOutlined, IdcardOutlined, ImportOutlined, InboxOutlined,
  OrderedListOutlined, PercentageOutlined, ScheduleOutlined, SettingOutlined, ShopOutlined, ShoppingCartOutlined,
  SolutionOutlined, SwapOutlined, TableOutlined, TeamOutlined, UserOutlined, WalletOutlined,
} from '@ant-design/icons'
import type { ComponentType } from 'react'
import type { Role } from '../api/types'

export interface NavItem {
  key: string
  label: string
  roles: Role[] | 'all'
  group?: string
  icon: ComponentType
}

// Администратор видит всё; пустой список ролей — только администратор
export const NAV: NavItem[] = [
  { key: '/', label: 'Главная', roles: 'all', icon: HomeOutlined },
  { key: '/feed', label: 'Живая лента', roles: 'all', icon: MessageOutlined },
  { key: '/analytics', label: 'Аналитика', roles: ['sales', 'accountant', 'shop_head', 'technologist', 'storekeeper'], icon: BarChartOutlined },
  { key: '/orders', label: 'Заказы клиентов', roles: ['sales', 'accountant', 'storekeeper', 'shop_head'], group: 'Продажи', icon: ShoppingCartOutlined },
  { key: '/clients', label: 'Клиенты', roles: ['sales', 'accountant'], group: 'Продажи', icon: TeamOutlined },
  { key: '/tasks', label: 'Задания', roles: ['shop_head', 'technologist', 'storekeeper', 'accountant', 'sales'], group: 'Производство', icon: ScheduleOutlined },
  { key: '/items', label: 'Номенклатура', roles: 'all', group: 'Производство', icon: AppstoreOutlined },
  { key: '/recipes', label: 'Рецептуры', roles: ['technologist', 'shop_head', 'accountant'], group: 'Производство', icon: ExperimentOutlined },
  { key: '/stock', label: 'Остатки', roles: 'all', group: 'Склад', icon: InboxOutlined },
  { key: '/shipments', label: 'Отгрузки', roles: ['storekeeper', 'sales', 'accountant'], group: 'Склад', icon: CarOutlined },
  { key: '/moves', label: 'Движения', roles: ['storekeeper', 'accountant', 'shop_head'], group: 'Склад', icon: SwapOutlined },
  { key: '/purchase-orders', label: 'Заявки поставщикам', roles: ['storekeeper', 'accountant'], group: 'Закупки', icon: FileTextOutlined },
  { key: '/receipts', label: 'Приёмки', roles: ['storekeeper', 'accountant'], group: 'Закупки', icon: ImportOutlined },
  { key: '/suppliers', label: 'Поставщики', roles: ['storekeeper', 'accountant'], group: 'Закупки', icon: ShopOutlined },
  { key: '/invoices', label: 'Счета покупателям', roles: ['accountant', 'sales'], group: 'Бухгалтерия', icon: FileDoneOutlined },
  { key: '/payments', label: 'Платежи', roles: ['accountant', 'sales'], group: 'Бухгалтерия', icon: WalletOutlined },
  { key: '/journal', label: 'Журнал операций', roles: ['accountant'], group: 'Бухгалтерия', icon: BookOutlined },
  { key: '/finance', label: 'Финансовые отчёты', roles: ['accountant'], group: 'Бухгалтерия', icon: FundOutlined },
  { key: '/accounts', label: 'План счетов', roles: ['accountant'], group: 'Бухгалтерия', icon: OrderedListOutlined },
  { key: '/payroll', label: 'Зарплата', roles: ['accountant'], group: 'Бухгалтерия', icon: DollarOutlined },
  { key: '/payroll-rates', label: 'Ставки удержаний', roles: ['accountant', 'hr'], group: 'Бухгалтерия', icon: PercentageOutlined },
  { key: '/employees', label: 'Сотрудники', roles: ['hr', 'accountant', 'shop_head'], group: 'Кадры', icon: IdcardOutlined },
  { key: '/hr-orders', label: 'Кадровые приказы', roles: ['hr', 'accountant'], group: 'Кадры', icon: SolutionOutlined },
  { key: '/absences', label: 'Отсутствия', roles: ['hr', 'accountant', 'shop_head'], group: 'Кадры', icon: CalendarOutlined },
  { key: '/timesheet', label: 'Табель', roles: ['hr', 'accountant', 'shop_head'], group: 'Кадры', icon: TableOutlined },
  { key: '/worktime', label: 'Учёт времени', roles: ['hr', 'accountant'], group: 'Кадры', icon: FieldTimeOutlined },
  { key: '/references', label: 'Справочники', roles: ['technologist', 'hr'], group: 'Настройки', icon: SettingOutlined },
  { key: '/users', label: 'Пользователи', roles: [], group: 'Настройки', icon: UserOutlined },
]

export const navRoles = (key: string) => NAV.find((i) => i.key === key)?.roles ?? []

/** Раздел меню для пути: /orders/5 → «Заказы клиентов». */
export const navSection = (pathname: string) => NAV.find((i) => i.key === '/' + pathname.split('/')[1])
