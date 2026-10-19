import type { Dayjs } from 'dayjs'
import { toApiDate } from '../utils/format'

type Option = { value: string | number; label: string }
export type Range = [Dayjs | null, Dayjs | null]

export type FilterField =
  | { key: string; label: string; type: 'select'; options: Option[]; multiple?: boolean }
  /** params — имена параметров API для начала и конца периода */
  | { key: string; label: string; type: 'dateRange'; params: [string, string] }
  | { key: string; label: string; type: 'switch' }

export type FilterValues = Record<string, unknown>

/** Встроенный пресет. values — функция: «сегодня» и «этот месяц» считаются в момент выбора. */
export interface FilterPreset {
  key: string
  label: string
  values: () => FilterValues
}

export const empty = (v: unknown) => v == null || v === false || v === '' || (Array.isArray(v) && v.every((x) => x == null || x === ''))

/** Только заполненные поля — пресеты сравниваются по ним. */
export function clean(fields: FilterField[], values: FilterValues): FilterValues {
  return Object.fromEntries(fields.filter((f) => !empty(values[f.key])).map((f) => [f.key, values[f.key]]))
}

/** Значения фильтра → параметры запроса к API. */
export function filterParams(fields: FilterField[], values: FilterValues): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  for (const f of fields) {
    const v = values[f.key]
    if (empty(v)) continue
    if (f.type === 'dateRange') {
      const [from, to] = v as Range
      params[f.params[0]] = toApiDate(from ?? undefined)
      params[f.params[1]] = toApiDate(to ?? undefined)
    } else params[f.key] = v
  }
  return params
}
