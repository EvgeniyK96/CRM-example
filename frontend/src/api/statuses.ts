export interface StatusInfo { color: string; label: string }

export const RECIPE_STATUS: Record<string, StatusInfo> = {
  draft: { color: 'blue', label: 'Черновик' },
  active: { color: 'green', label: 'Активна' },
  archived: { color: 'default', label: 'В архиве' },
}

export const PO_STATUS: Record<string, StatusInfo> = {
  draft: { color: 'blue', label: 'Черновик' },
  sent: { color: 'gold', label: 'Отправлена' },
  partial: { color: 'orange', label: 'Получена частично' },
  received: { color: 'green', label: 'Получена' },
  cancelled: { color: 'default', label: 'Отменена' },
}

export const RECEIPT_STATUS: Record<string, StatusInfo> = {
  draft: { color: 'blue', label: 'Черновик' },
  posted: { color: 'green', label: 'Проведена' },
}

export const MOVE_KIND: Record<string, StatusInfo> = {
  receipt: { color: 'green', label: 'Приход от поставщика' },
  production_out: { color: 'orange', label: 'Списание в производство' },
  production_in: { color: 'cyan', label: 'Выпуск продукции' },
  shipment: { color: 'blue', label: 'Отгрузка клиенту' },
  write_off: { color: 'red', label: 'Списание' },
  adjustment: { color: 'purple', label: 'Корректировка' },
}

export const statusOptions = (map: Record<string, StatusInfo>) =>
  Object.entries(map).map(([value, s]) => ({ value, label: s.label }))

export const SALES_ORDER_STATUS: Record<string, StatusInfo> = {
  new: { color: 'blue', label: 'Новый' },
  confirmed: { color: 'gold', label: 'Подтверждён' },
  in_production: { color: 'orange', label: 'В производстве' },
  ready: { color: 'cyan', label: 'Готов к отгрузке' },
  shipped: { color: 'green', label: 'Отгружен' },
  cancelled: { color: 'default', label: 'Отменён' },
}

export const CLIENT_KIND: Record<string, StatusInfo> = {
  wholesale: { color: 'purple', label: 'Опт' },
  store: { color: 'blue', label: 'Магазин' },
  brand_store: { color: 'magenta', label: 'Фирменный' },
}

export const TASK_STATUS: Record<string, StatusInfo> = {
  planned: { color: 'blue', label: 'Запланировано' },
  in_progress: { color: 'orange', label: 'В работе' },
  done: { color: 'green', label: 'Выполнено' },
  cancelled: { color: 'default', label: 'Отменено' },
}

export const INVOICE_STATUS: Record<string, StatusInfo> = {
  unpaid: { color: 'red', label: 'Не оплачен' },
  partial: { color: 'orange', label: 'Оплачен частично' },
  paid: { color: 'green', label: 'Оплачен' },
}

export const ENTRY_SOURCE: Record<string, StatusInfo> = {
  manual: { color: 'purple', label: 'Ручная' },
  receipt: { color: 'blue', label: 'Приёмка' },
  production_start: { color: 'orange', label: 'Запуск производства' },
  production_finish: { color: 'cyan', label: 'Выпуск' },
  shipment: { color: 'green', label: 'Отгрузка' },
  write_off: { color: 'red', label: 'Списание' },
  opening: { color: 'default', label: 'Начальные остатки' },
  payment: { color: 'gold', label: 'Платёж' },
  payroll: { color: 'magenta', label: 'Зарплата' },
  payroll_payment: { color: 'magenta', label: 'Выплата зарплаты' },
}

/** Ссылка на документ-основание проводки во фронтенде */
export const entrySourcePath = (type: string, id: number | null): string | null => {
  if (id == null) return null
  const paths: Record<string, string> = {
    receipt: '/receipts', production_start: '/tasks', production_finish: '/tasks', shipment: '/shipments', opening: '/trace',
    payroll: '/payroll', payroll_payment: '/payroll',
  }
  return paths[type] ? `${paths[type]}/${id}` : null
}

export const HR_ORDER_KIND: Record<string, StatusInfo> = {
  hire: { color: 'green', label: 'Приём' },
  transfer: { color: 'blue', label: 'Перевод' },
  salary: { color: 'gold', label: 'Изменение оклада' },
  dismissal: { color: 'red', label: 'Увольнение' },
}

export const ABSENCE_KIND: Record<string, StatusInfo> = {
  vacation: { color: 'green', label: 'Ежегодный отпуск' },
  sick: { color: 'red', label: 'Больничный' },
  business_trip: { color: 'blue', label: 'Командировка' },
  unpaid: { color: 'default', label: 'Без содержания' },
}

export const PAYROLL_STATUS: Record<string, StatusInfo> = {
  draft: { color: 'blue', label: 'Черновик' },
  posted: { color: 'gold', label: 'Проведена' },
  paid: { color: 'green', label: 'Выплачена' },
}

/** Статусы по типу документа ленты (ключ — app_label.model, как в API /activity/) */
export const ACTIVITY_TARGET_STATUS: Record<string, Record<string, StatusInfo>> = {
  'sales.salesorder': SALES_ORDER_STATUS,
  'production.productiontask': TASK_STATUS,
  'purchasing.purchaseorder': PO_STATUS,
  'purchasing.receipt': RECEIPT_STATUS,
  'recipes.recipe': RECIPE_STATUS,
}
