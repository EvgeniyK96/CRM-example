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
