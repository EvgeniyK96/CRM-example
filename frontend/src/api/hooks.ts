import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App } from 'antd'
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

/** Карточка объекта. Ключ [url, id] — инвалидируется вместе со списком по префиксу url. */
export function useDetail<T>(url: string, id: string | number | undefined) {
  return useQuery({
    queryKey: [url, String(id)],
    queryFn: async () => (await api.get<T>(`${url}${id}/`)).data,
    enabled: id != null,
  })
}

interface ActionOptions<R> {
  success?: string | ((result: R) => string)
  /** Префиксы ключей запросов для обновления; 'all' — обновить всё (операция затронула несколько разделов) */
  invalidate?: string[] | 'all'
  onSuccess?: (result: R) => void
}

/** Мутация с уведомлением об успехе/ошибке и обновлением связанных данных. */
export function useApiAction<R = unknown, V = void>(fn: (vars: V) => Promise<R>, opts: ActionOptions<R> = {}) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      if (opts.invalidate === 'all') qc.invalidateQueries()
      else opts.invalidate?.forEach((key) => qc.invalidateQueries({ queryKey: [key] }))
      if (opts.success) message.success(typeof opts.success === 'function' ? opts.success(result) : opts.success)
      opts.onSuccess?.(result)
    },
    onError: (e) => message.error(errorText(e)),
  })
}
