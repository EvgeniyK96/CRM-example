import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons'
import { Card } from 'antd'
import type { ReactNode } from 'react'
import { CHART } from './theme'

interface Props {
  label: string
  value: string
  /** Изменение к прошлому периоду, %; знак + направление «хорошо/плохо» */
  delta?: number | null
  deltaLabel?: string
  upIsGood?: boolean
  hint?: ReactNode
  /** Значение требует внимания (просрочка, дефицит) — иконка + подпись, не только цвет */
  alert?: boolean
}

export default function StatTile({ label, value, delta, deltaLabel = 'к прошлому периоду', upIsGood = true, hint, alert }: Props) {
  const good = delta != null && (delta >= 0) === upIsGood
  return (
    <Card size="small" style={{ height: '100%' }}>
      <div style={{ color: CHART.textSecondary, fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 600, color: alert ? CHART.critical : CHART.textPrimary, lineHeight: 1.3 }}>{value}</div>
      {delta != null && (
        <div style={{ fontSize: 12, color: good ? CHART.deltaGood : CHART.critical }}>
          {delta >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {delta >= 0 ? '+' : '−'}{Math.abs(delta).toFixed(1)}%{' '}
          <span style={{ color: CHART.muted }}>{deltaLabel}</span>
        </div>
      )}
      {hint && <div style={{ fontSize: 12, color: CHART.muted }}>{hint}</div>}
    </Card>
  )
}
