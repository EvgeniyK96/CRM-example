import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

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

/** «5 минут назад»; старше недели — дата и время */
export const fmtAgo = (value: string) =>
  dayjs().diff(value, 'day') >= 7 ? fmtDateTime(value) : dayjs(value).fromNow()

/** Секунды → «7:05» (часы:минуты) */
export const fmtDuration = (seconds: number) => {
  const m = Math.max(0, Math.floor(seconds / 60))
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}`
}

export const fmtTime = (value: string | null | undefined) => (value ? dayjs(value).format('HH:mm') : '—')
