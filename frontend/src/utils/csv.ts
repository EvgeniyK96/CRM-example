export interface CsvColumn<T> { title: string; value: (row: T) => string | number | null | undefined }

/**
 * Выгрузка таблицы в CSV для Excel: разделитель «;», BOM для кириллицы,
 * числа с запятой (как ждёт русская локаль Excel).
 */
export function exportCsv<T>(filename: string, columns: CsvColumn<T>[], rows: T[]) {
  const cell = (v: string | number | null | undefined) => {
    if (v == null) return ''
    const text = typeof v === 'number' ? String(v).replace('.', ',') : /^-?\d+\.\d+$/.test(v) ? v.replace('.', ',') : v
    return /[;"\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const lines = [columns.map((c) => cell(c.title)).join(';'), ...rows.map((r) => columns.map((c) => cell(c.value(r))).join(';'))]
  const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
