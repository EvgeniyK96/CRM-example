import { CloseOutlined, DeleteOutlined, FilterOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Checkbox, DatePicker, Form, Input, Popover, Select, Tooltip } from 'antd'
import dayjs from 'dayjs'
import { useState, type KeyboardEvent } from 'react'
import { fmtDate, toApiDate } from '../utils/format'
import { clean, filterParams, type FilterField, type FilterPreset, type FilterValues, type Range } from './filters'

interface SavedPreset {
  key: string
  label: string
  values: FilterValues
}

// Сохранённые пресеты живут в браузере (удобство конкретного пользователя); даты храним строками
const toStored = (fields: FilterField[], values: FilterValues) => Object.fromEntries(Object.entries(values).map(([k, v]) =>
  [k, fields.find((f) => f.key === k)?.type === 'dateRange' ? (v as Range).map((d) => toApiDate(d ?? undefined) ?? null) : v]))
const fromStored = (fields: FilterField[], values: FilterValues) => Object.fromEntries(Object.entries(values).map(([k, v]) =>
  [k, fields.find((f) => f.key === k)?.type === 'dateRange' ? (v as (string | null)[]).map((d) => (d ? dayjs(d) : null)) : v]))

function readSaved(storageKey: string): SavedPreset[] {
  try {
    return JSON.parse(localStorage.getItem(storageKey) ?? '[]') as SavedPreset[]
  } catch {
    return []
  }
}

function writeSaved(storageKey: string, presets: SavedPreset[]) {
  try {
    localStorage.setItem(storageKey, JSON.stringify(presets))
  } catch {
    // не сохранится — пресет проживёт до перезагрузки
  }
}

/** Подпись поля в строке фильтра: «Статус: Новый, Подтверждён». */
function summary(field: FilterField, value: unknown): string {
  if (field.type === 'switch') return field.label
  if (field.type === 'dateRange') {
    const [from, to] = value as Range
    if (from && to && from.isSame(to, 'day')) return `${field.label}: ${fmtDate(toApiDate(from))}`
    return `${field.label}: ${from ? `с ${fmtDate(toApiDate(from))}` : ''}${from && to ? ' ' : ''}${to ? `по ${fmtDate(toApiDate(to))}` : ''}`
  }
  const list = (Array.isArray(value) ? value : [value]).map((v) => field.options.find((o) => o.value === v)?.label ?? String(v))
  return `${field.label}: ${list.length > 2 ? `${list.slice(0, 2).join(', ')} +${list.length - 2}` : list.join(', ')}`
}

interface Props {
  fields: FilterField[]
  presets?: FilterPreset[]
  value: FilterValues
  onChange: (values: FilterValues) => void
  search: string
  onSearch: (text: string) => void
  searchPlaceholder?: string
  /** Ключ localStorage для пресетов пользователя; без него сохранять нельзя */
  storageKey?: string
}

/**
 * Единая строка «Фильтр + поиск» в стиле Битрикс24: активные условия — плашками внутри поля поиска,
 * по клику открывается панель с пресетами слева и полями фильтра справа.
 */
export default function FilterBar({ fields, presets = [], value, onChange, search, onSearch, searchPlaceholder, storageKey }: Props) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(search)
  const [saved, setSaved] = useState<SavedPreset[]>(() => (storageKey ? readSaved(storageKey) : []))
  const [naming, setNaming] = useState<string | null>(null)
  const [form] = Form.useForm()

  const current = clean(fields, value)
  const same = (values: FilterValues) =>
    JSON.stringify(filterParams(fields, current)) === JSON.stringify(filterParams(fields, clean(fields, values)))
  const allPresets = [
    ...presets.map((p) => ({ key: p.key, label: p.label, values: p.values, own: false })),
    ...saved.map((p) => ({ key: p.key, label: p.label, values: () => fromStored(fields, p.values), own: true })),
  ]
  const active = Object.keys(current).length > 0 ? allPresets.find((p) => same(p.values())) : undefined

  const toggle = (o: boolean) => {
    if (o) form.setFieldsValue(Object.fromEntries(fields.map((f) => [f.key, value[f.key]])))
    setOpen(o)
  }
  const apply = (values: FilterValues) => {
    onChange(clean(fields, values))
    setOpen(false)
  }
  const remove = (key: string) => onChange(Object.fromEntries(Object.entries(current).filter(([k]) => k !== key)))
  const savePreset = () => {
    if (!storageKey || !naming?.trim()) return
    const next = [...saved, { key: `own-${Date.now()}`, label: naming.trim(), values: toStored(fields, clean(fields, form.getFieldsValue())) }]
    setSaved(next)
    writeSaved(storageKey, next)
    setNaming(null)
  }
  const deletePreset = (key: string) => {
    const next = saved.filter((p) => p.key !== key)
    setSaved(next)
    if (storageKey) writeSaved(storageKey, next)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch(text.trim())
      setOpen(false)
    }
    if (e.key === 'Escape') setOpen(false)
    // Backspace в пустом поле убирает последнее условие — как в Битрикс24
    if (e.key === 'Backspace' && !text) {
      if (active) onChange({})
      else {
        const keys = Object.keys(current)
        if (keys.length) remove(keys[keys.length - 1])
      }
    }
  }

  const panel = (
    <div className="filter-panel">
      {allPresets.length > 0 && (
        <nav className="filter-presets" aria-label="Пресеты фильтра">
          {allPresets.map((p) => (
            <div key={p.key} className={`filter-preset${active?.key === p.key ? ' filter-preset-active' : ''}`}>
              <button type="button" onClick={() => apply(p.values())}>{p.label}</button>
              {p.own && (
                <Tooltip title="Удалить пресет">
                  <Button type="text" size="small" icon={<DeleteOutlined />} aria-label={`Удалить пресет ${p.label}`}
                    onClick={() => deletePreset(p.key)} />
                </Tooltip>
              )}
            </div>
          ))}
        </nav>
      )}
      <Form form={form} layout="vertical" className="filter-fields" onFinish={apply}>
        <div className="filter-grid">
          {fields.map((f) => (
            <Form.Item key={f.key} name={f.key} label={f.type === 'switch' ? undefined : f.label}
              valuePropName={f.type === 'switch' ? 'checked' : 'value'} style={{ marginBottom: 12 }}>
              {f.type === 'select' ? (
                <Select allowClear mode={f.multiple ? 'multiple' : undefined} options={f.options} placeholder="Любой"
                  showSearch={{ optionFilterProp: 'label' }} maxTagCount="responsive" />
              ) : f.type === 'dateRange' ? (
                <DatePicker.RangePicker allowEmpty={[true, true]} style={{ width: '100%' }} format="DD.MM.YYYY" />
              ) : (
                <Checkbox>{f.label}</Checkbox>
              )}
            </Form.Item>
          ))}
        </div>
        <div className="filter-actions">
          <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>Найти</Button>
          <Button onClick={() => apply({})}>Сбросить</Button>
          {storageKey && (naming === null ? (
            <Button type="link" onClick={() => setNaming('')}>Сохранить как пресет</Button>
          ) : (
            <span className="filter-naming">
              <Input autoFocus size="middle" placeholder="Название" value={naming} onChange={(e) => setNaming(e.target.value)}
                onPressEnter={(e) => { e.preventDefault(); savePreset() }} style={{ width: 180 }} />
              <Button onClick={savePreset} disabled={!naming.trim()}>Сохранить</Button>
              <Button type="text" icon={<CloseOutlined />} aria-label="Не сохранять" onClick={() => setNaming(null)} />
            </span>
          ))}
        </div>
      </Form>
    </div>
  )

  return (
    <Popover open={open} onOpenChange={toggle}
      trigger="click" placement="bottomLeft" arrow={false} content={panel} destroyOnHidden={false}
      styles={{ container: { padding: 0 } }}>
      <div className="filter-bar" role="search">
        <FilterOutlined className="filter-bar-icon" aria-hidden />
        {active ? (
          <span className="filter-chip filter-chip-preset">
            {active.label}
            <button type="button" aria-label="Сбросить фильтр" onClick={(e) => { e.stopPropagation(); onChange({}) }}><CloseOutlined /></button>
          </span>
        ) : (
          fields.filter((f) => f.key in current).map((f) => (
            <span key={f.key} className="filter-chip">
              {summary(f, current[f.key])}
              <button type="button" aria-label={`Убрать условие ${f.label}`} onClick={(e) => { e.stopPropagation(); remove(f.key) }}>
                <CloseOutlined />
              </button>
            </span>
          ))
        )}
        <input className="filter-bar-input" value={text} placeholder={Object.keys(current).length ? '+ поиск' : (searchPlaceholder ?? 'Фильтр + поиск')}
          aria-label="Поиск" onChange={(e) => { setText(e.target.value); if (!e.target.value) onSearch('') }}
          onKeyDown={onKeyDown} onClick={(e) => { e.stopPropagation(); if (!open) toggle(true) }} />
        {(text || Object.keys(current).length > 0) && (
          <button type="button" className="filter-bar-clear" aria-label="Очистить фильтр и поиск"
            onClick={(e) => { e.stopPropagation(); setText(''); onSearch(''); onChange({}) }}>
            <CloseOutlined />
          </button>
        )}
        <button type="button" className="filter-bar-search" aria-label="Найти" onClick={(e) => { e.stopPropagation(); onSearch(text.trim()) }}>
          <SearchOutlined />
        </button>
      </div>
    </Popover>
  )
}
