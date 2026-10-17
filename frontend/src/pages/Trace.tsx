import { useQuery } from '@tanstack/react-query'
import { Card, Descriptions, Empty, Space, Table, Typography } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { LotTrace, TraceLot } from '../api/types'
import { fmtDate, fmtDateTime, fmtQty } from '../utils/format'

const lotLink = (lot: TraceLot) => <Link to={`/trace/${lot.id}`}>{lot.number}</Link>

/** Прослеживаемость партии: из чего сделана продукция и куда ушло сырьё. */
export default function Trace() {
  const { lotId } = useParams()
  const { data, isLoading } = useQuery({
    queryKey: ['/production/trace/', lotId],
    queryFn: async () => (await api.get<LotTrace>(`/production/trace/${lotId}/`)).data,
  })

  if (isLoading || !data) return <Card loading />
  const { lot, produced_by: task } = data

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Card title={`Партия ${lot.number}: ${lot.item_name}`}>
        <Descriptions size="small" column={{ xs: 1, md: 3 }} items={[
          { label: 'Дата', children: fmtDate(lot.date) },
          { label: 'Годен до', children: fmtDate(lot.expiry_date) },
          { label: 'Поставщик', children: lot.supplier_name ?? '—' },
          ...(task ? [
            { label: 'Произведена', children: <Link to={`/tasks/${task.id}`}>{task.number}</Link> },
            { label: 'Цех', children: task.department_name },
            { label: 'Рецептура', children: `версия ${task.recipe_version}, ${fmtDateTime(task.finished_at)}` },
          ] : []),
        ]} />
      </Card>

      {task && (
        <Card size="small" title="Сделана из партий сырья">
          <Table rowKey={(r) => `${r.id}-${r.quantity}`} size="small" pagination={false} dataSource={data.ingredients} columns={[
            { title: 'Сырьё', dataIndex: 'item_name' },
            { title: 'Партия', render: (_, r) => lotLink(r) },
            { title: 'Поставщик', dataIndex: 'supplier_name', render: (v) => v ?? '—' },
            { title: 'Поступила', dataIndex: 'date', render: fmtDate },
            { title: 'Годна до', dataIndex: 'expiry_date', render: fmtDate },
            { title: 'Использовано', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
          ]} />
        </Card>
      )}

      {data.used_in.length > 0 && (
        <Card size="small" title="Использована в производстве">
          <Table rowKey={(r) => `${r.task}-${r.quantity}`} size="small" pagination={false} dataSource={data.used_in} columns={[
            { title: 'Задание', render: (_, r) => <Link to={`/tasks/${r.task}`}>{r.task_number}</Link> },
            { title: 'Количество', align: 'right', render: (_, r) => fmtQty(r.quantity, lot.unit_code) },
            { title: 'Партия продукции', render: (_, r) => (r.output_lot ? lotLink(r.output_lot) : <Typography.Text type="secondary">задание ещё в работе</Typography.Text>) },
            { title: 'Продукт', render: (_, r) => r.output_lot?.item_name ?? '—' },
          ]} />
        </Card>
      )}

      {data.shipped_to.length > 0 && (
        <Card size="small" title="Отгружена клиентам">
          <Table rowKey={(r) => `${r.shipment}-${r.quantity}`} size="small" pagination={false} dataSource={data.shipped_to} columns={[
            { title: 'Накладная', render: (_, r) => <Link to={`/shipments/${r.shipment}`}>{r.shipment_number}</Link> },
            { title: 'Дата', dataIndex: 'date', render: fmtDate },
            { title: 'Клиент', dataIndex: 'client_name' },
            { title: 'Заказ', render: (_, r) => <Link to={`/orders/${r.order}`}>{r.order_number}</Link> },
            { title: 'Количество', align: 'right', render: (_, r) => fmtQty(r.quantity, lot.unit_code) },
          ]} />
        </Card>
      )}

      {!task && data.used_in.length === 0 && data.shipped_to.length === 0 && (
        <Card><Empty description="Партия ещё не участвовала в производстве" /></Card>
      )}
    </Space>
  )
}
