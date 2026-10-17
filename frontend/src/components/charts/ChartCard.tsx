import { Card, Segmented } from 'antd'
import { useState, type ReactNode } from 'react'

/** Карточка графика с переключателем на табличный вид (значения доступны без наведения и без цвета). */
export default function ChartCard({ title, chart, table, empty }: {
  title: string
  chart: ReactNode
  table: ReactNode
  empty?: boolean
}) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  return (
    <Card size="small" title={title} style={{ height: '100%' }}
      extra={!empty && <Segmented size="small" value={view} onChange={setView}
        options={[{ value: 'chart', label: 'График' }, { value: 'table', label: 'Таблица' }]} />}>
      {empty ? <div style={{ color: '#898781', padding: '24px 0', textAlign: 'center' }}>Нет данных за период</div>
        : view === 'chart' ? chart : table}
    </Card>
  )
}
