import { ExclamationCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Card, Col, Row, Table, Tag } from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Dashboard as DashboardData, ExpiringLot } from '../api/types'
import { fmtDate, fmtMoney, fmtQty } from '../utils/format'
import ChartCard from './charts/ChartCard'
import { BarList, StackedBars, TrendChart } from './charts/Charts'
import StatTile from './charts/StatTile'
import { defaultPeriod, periodParams, type Period } from '../utils/period'
import PeriodFilter from './PeriodFilter'

const money0 = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 })
const fmtTenge = (v: number | string) => `${money0.format(Number(v))} ₸`

function ExpiryTag({ lot }: { lot: ExpiringLot }) {
  // Статус — иконка + подпись, цвет лишь дублирует
  return lot.status === 'expired'
    ? <Tag color="red" icon={<ExclamationCircleOutlined />}>просрочена</Tag>
    : <Tag color="orange" icon={<WarningOutlined />}>{lot.days_left} дн.</Tag>
}

/** Дашборд главной страницы: KPI и графики по разделам, доступным роли. */
export default function Dashboard() {
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const params = periodParams(period)
  const { data, isFetching } = useQuery({
    queryKey: ['/reports/dashboard/', params],
    queryFn: async () => (await api.get<DashboardData>('/reports/dashboard/', { params })).data,
    placeholderData: keepPreviousData, // при смене периода держим прошлую картинку, без мигания
  })
  if (!data) return <Card loading />
  if (!data.sections.length) return null

  const { sales, finance, production, warehouse } = data
  const delta = sales && Number(sales.revenue_prev) > 0
    ? ((Number(sales.revenue) - Number(sales.revenue_prev)) / Number(sales.revenue_prev)) * 100 : null
  const inWork = sales ? sales.orders.confirmed + sales.orders.in_production + sales.orders.ready : 0
  const margin = sales && Number(sales.revenue) ? (Number(sales.gross_profit) / Number(sales.revenue)) * 100 : null
  const tile = { xs: 24, sm: 12, lg: 6 } as const

  return (
    <div style={{ opacity: isFetching ? 0.6 : 1, transition: 'opacity .2s' }}>
      <PeriodFilter value={period} onChange={setPeriod} />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {sales && <Col {...tile}><StatTile label="Выручка" value={fmtTenge(sales.revenue)} delta={delta} /></Col>}
        {sales && (
          <Col {...tile}>
            <StatTile label="Валовая прибыль" value={fmtTenge(sales.gross_profit)}
              hint={margin != null ? `маржа ${margin.toFixed(1)}%` : undefined} />
          </Col>
        )}
        {sales && <Col {...tile}><StatTile label="Заказов в работе" value={String(inWork)} hint={`готовы к отгрузке: ${sales.orders.ready}`} /></Col>}
        {finance && (
          <Col {...tile}>
            <StatTile label="Дебиторская задолженность" value={fmtTenge(finance.receivables)}
              alert={Number(finance.overdue) > 0} hint={`просрочено ${fmtTenge(finance.overdue)}`} />
          </Col>
        )}
        {warehouse && <Col {...tile}><StatTile label="Запасы сырья" value={fmtTenge(warehouse.raw_value)} hint={`продукция ${fmtTenge(warehouse.product_value)}`} /></Col>}
        {warehouse && (
          <Col {...tile}>
            <StatTile label="Сырьё ниже минимума" value={`${warehouse.below_min.length} поз.`} alert={warehouse.below_min.length > 0}
              hint={<Link to="/stock">к остаткам</Link>} />
          </Col>
        )}
        {warehouse && (
          <Col {...tile}>
            <StatTile label="Просрочено на складе" value={fmtTenge(warehouse.expired_value)} alert={Number(warehouse.expired_value) > 0}
              hint="требует списания" />
          </Col>
        )}
      </Row>

      <Row gutter={[16, 16]}>
        {sales && (
          <Col xs={24} xl={14}>
            <ChartCard title="Выручка по дням" empty={!Number(sales.revenue)}
              chart={<TrendChart data={sales.by_day} x="date" y="revenue" format={fmtTenge} xFormat={(d) => dayjs(d).format('DD.MM')} />}
              table={<Table rowKey="date" size="small" pagination={{ pageSize: 10, hideOnSinglePage: true }}
                dataSource={sales.by_day.filter((d) => Number(d.revenue))}
                columns={[{ title: 'Дата', dataIndex: 'date', render: fmtDate }, { title: 'Выручка', dataIndex: 'revenue', align: 'right', render: fmtMoney }]} />} />
          </Col>
        )}
        {sales && (
          <Col xs={24} xl={10}>
            <ChartCard title="Продукты: выручка" empty={!sales.top_products.length}
              chart={<BarList data={sales.top_products} label="name" value="revenue" format={fmtTenge} />}
              table={<Table rowKey="product" size="small" pagination={false} dataSource={sales.top_products} columns={[
                { title: 'Продукт', dataIndex: 'name' },
                { title: 'Кол-во', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
                { title: 'Выручка', dataIndex: 'revenue', align: 'right', render: fmtMoney },
                { title: 'Маржа', dataIndex: 'margin_percent', align: 'right', render: (v) => (v == null ? '—' : `${v}%`) },
              ]} />} />
          </Col>
        )}
        {production && (
          <Col xs={24} xl={12}>
            <ChartCard title="Загрузка цехов, заданий" empty={!production.load.length}
              chart={<StackedBars data={production.load} label="name" format={(v) => String(v)} series={[
                { key: 'planned', name: 'В очереди' }, { key: 'in_progress', name: 'В работе' }, { key: 'done', name: 'Выполнено за период' },
              ]} />}
              table={<Table rowKey="department" size="small" pagination={false} dataSource={production.load} columns={[
                { title: 'Цех', dataIndex: 'name' }, { title: 'В очереди', dataIndex: 'planned', align: 'right' },
                { title: 'В работе', dataIndex: 'in_progress', align: 'right' }, { title: 'Выполнено', dataIndex: 'done', align: 'right' },
              ]} />} />
          </Col>
        )}
        {production && (
          <Col xs={24} xl={12}>
            <ChartCard title="Брак по продуктам, %" empty={!production.output.length}
              chart={<BarList data={production.output} label="name" value="defect_percent" format={(v) => `${v.toFixed(1)}%`} />}
              table={<Table rowKey="product" size="small" pagination={false} dataSource={production.output} columns={[
                { title: 'Продукт', dataIndex: 'name' }, { title: 'Цех', dataIndex: 'department_name' },
                { title: 'Выпуск', align: 'right', render: (_, r) => fmtQty(r.output, r.unit_code) },
                { title: 'Брак', align: 'right', render: (_, r) => fmtQty(r.defect, r.unit_code) },
                { title: '%', dataIndex: 'defect_percent', align: 'right' },
              ]} />} />
          </Col>
        )}
        {warehouse && warehouse.below_min.length > 0 && (
          <Col xs={24} xl={12}>
            <Card size="small" title="Сырьё ниже минимального остатка">
              <Table rowKey="item" size="small" pagination={false} dataSource={warehouse.below_min} columns={[
                { title: 'Сырьё', dataIndex: 'name' },
                { title: 'Доступно', align: 'right', render: (_, r) => fmtQty(r.available, r.unit_code) },
                { title: 'Минимум', align: 'right', render: (_, r) => fmtQty(r.min_stock, r.unit_code) },
                { title: 'Докупить', align: 'right', render: (_, r) => <b>{fmtQty(r.shortage, r.unit_code)}</b> },
              ]} />
            </Card>
          </Col>
        )}
        {warehouse && warehouse.expiring.length > 0 && (
          <Col xs={24} xl={12}>
            <Card size="small" title="Сроки годности: просрочено и истекает">
              <Table rowKey="lot" size="small" pagination={false} dataSource={warehouse.expiring} columns={[
                { title: 'Партия', render: (_, r) => <Link to={`/trace/${r.lot}`}>{r.number}</Link> },
                { title: 'Номенклатура', dataIndex: 'name' },
                { title: 'Остаток', align: 'right', render: (_, r) => fmtQty(r.balance, r.unit_code) },
                { title: 'Годна до', dataIndex: 'expiry_date', render: fmtDate },
                { title: 'Срок', render: (_, r) => <ExpiryTag lot={r} /> },
              ]} />
            </Card>
          </Col>
        )}
      </Row>
    </div>
  )
}
