import { CHART } from './theme'

interface Item { name?: unknown; value?: unknown; color?: string; dataKey?: unknown }

interface Props {
  active?: boolean
  label?: string | number
  payload?: readonly Item[]
  format: (v: number) => string
  labelFormat?: (label: string | number) => string
}

/** Подсказка: значение — крупно и первым, название серии — вторично, ключ серии — короткой линией. */
export default function ChartTooltip({ active, label, payload, format, labelFormat }: Props) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#fff', border: '1px solid rgba(11,11,11,0.10)', borderRadius: 6, padding: '8px 10px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)', fontSize: 12 }}>
      {label != null && <div style={{ color: CHART.textSecondary, marginBottom: 4 }}>{labelFormat ? labelFormat(label) : label}</div>}
      {payload.map((p) => (
        <div key={String(p.dataKey ?? p.name)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 12, height: 2, background: p.color, display: 'inline-block' }} />
          <b style={{ color: CHART.textPrimary }}>{format(Number(p.value))}</b>
          {payload.length > 1 && <span style={{ color: CHART.textSecondary }}>{String(p.name)}</span>}
        </div>
      ))}
    </div>
  )
}
