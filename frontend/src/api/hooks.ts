import { useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { api, type Page } from './client'

/** Список из DRF-эндпоинта. Ключ запроса начинается с url — инвалидируем по нему. */
export function useList<T>(url: string, params: Record<string, unknown> = {}, enabled = true) {
  return useQuery({
    queryKey: [url, params],
    queryFn: async () => (await api.get<Page<T>>(url, { params: { page_size: 1000, ...params } })).data.results,
    enabled,
  })
}

export const toOptions = <T extends { id: number }>(rows: T[] | undefined, label: (row: T) => string) =>
  rows?.map((r) => ({ value: r.id, label: label(r) })) ?? []

/** Текст ошибки DRF: {"field": ["msg"]}, {"detail": "msg"} или ["msg"]. */
export function errorText(error: unknown): string {
  if (!isAxiosError(error)) return 'Неизвестная ошибка'
  const data = error.response?.data
  if (!data) return 'Сервер недоступен'
  const parts: string[] = []
  const walk = (value: unknown, field?: string) => {
    if (Array.isArray(value)) value.forEach((v) => walk(v, field))
    else if (value && typeof value === 'object')
      Object.entries(value).forEach(([k, v]) => walk(v, ['detail', 'non_field_errors'].includes(k) ? field : k))
    else if (value != null) parts.push(field ? `${field}: ${value}` : String(value))
  }
  walk(data)
  return parts.join('; ') || 'Ошибка запроса'
}

/** Ошибки полей DRF в формате antd Form.setFields. */
export function fieldErrors(error: unknown) {
  const data = isAxiosError(error) ? error.response?.data : null
  if (!data || typeof data !== 'object' || Array.isArray(data)) return []
  return Object.entries(data)
    .filter(([k, v]) => !['detail', 'non_field_errors'].includes(k) && Array.isArray(v) && typeof v[0] === 'string')
    .map(([name, errors]) => ({ name, errors: errors as string[] }))
}
