import dayjs from 'dayjs'

const qtyFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3 })
const moneyFormat = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const fmtQty = (value: string | number | null | undefined, unit?: string) =>
  value == null ? '—' : `${qtyFormat.format(Number(value))}${unit ? ` ${unit}` : ''}`

export const fmtMoney = (value: string | number | null | undefined) => (value == null ? '—' : moneyFormat.format(Number(value)))

export const fmtDate = (value: string | null | undefined) => (value ? dayjs(value).format('DD.MM.YYYY') : '—')

export const fmtDateTime = (value: string | null | undefined) => (value ? dayjs(value).format('DD.MM.YYYY HH:mm') : '—')

/** dayjs → 'YYYY-MM-DD' для DRF */
export const toApiDate = (value: dayjs.Dayjs | null | undefined) => value?.format('YYYY-MM-DD') ?? null
export const fromApiDate = (value: string | null | undefined) => (value ? dayjs(value) : null)
