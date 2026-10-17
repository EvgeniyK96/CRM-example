import { DownloadOutlined } from '@ant-design/icons'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Button, Card, Col, Row, Space, Table, Tabs, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { CLIENT_KIND } from '../api/statuses'
import type { ClientSales, ProductionOutput, ProductionReport, ProductSales, SalesReport, StockReport, StockValuation } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import StatTile from '../components/charts/StatTile'
import PeriodFilter from '../components/PeriodFilter'
import StatusTag from '../components/StatusTag'
import { exportCsv, type CsvColumn } from '../utils/csv'
import { fmtMoney, fmtQty } from '../utils/format'
import { defaultPeriod, periodParams, type Period } from '../utils/period'

function useReport<T>(url: string, params: Record<string, string>, enabled: boolean) {
  return useQuery({
    queryKey: [url, params],
    queryFn: async () => (await api.get<T>(url, { params })).data,
    enabled,
    placeholderData: keepPreviousData,
  })
}

/** Таблица отчёта с выгрузкой в CSV (столбцы выгрузки — те же данные, что на экране). */
function ReportTable<T extends object>({ title, filename, rows, columns, csv, rowKey }: {
  title: string
  filename: string
  rows: T[] | undefined
  columns: TableColumnsType<T>
  csv: CsvColumn<T>[]
  rowKey: keyof T & string
}) {
  return (
    <Card size="small" title={title}
      extra={<Button size="small" icon={<DownloadOutlined />} disabled={!rows?.length}
        onClick={() => rows && exportCsv(filename, csv, rows)}>CSV</Button>}>
      <Table<T> rowKey={rowKey} size="small" dataSource={rows} columns={columns} pagination={{ pageSize: 20, hideOnSinglePage: true }} />
    </Card>
  )
}

const marginCol = { title: 'Маржа, %', dataIndex: 'margin_percent', align: 'right' as const, render: (v: string | null) => (v == null ? '—' : v) }

function SalesTab({ params }: { params: Record<string, string> }) {
  const { data } = useReport<SalesReport>('/reports/sales/', params, true)
  const suffix = `${params.date_from}_${params.date_to}`
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}><StatTile label="Выручка" value={fmtMoney(data?.revenue)} /></Col>
        <Col xs={24} sm={8}><StatTile label="Себестоимость" value={fmtMoney(data?.cost)} /></Col>
        <Col xs={24} sm={8}><StatTile label="Валовая прибыль" value={fmtMoney(data?.gross_profit)} /></Col>
      </Row>
      <ReportTable<ProductSales> title="По продуктам" filename={`продажи_по_продуктам_${suffix}`} rowKey="product" rows={data?.by_product}
        columns={[
          { title: 'Продукт', dataIndex: 'name' },
          { title: 'Количество', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
          { title: 'Выручка', dataIndex: 'revenue', align: 'right', render: fmtMoney },
          { title: 'Себестоимость', dataIndex: 'cost', align: 'right', render: fmtMoney },
          { title: 'Маржа', dataIndex: 'margin', align: 'right', render: fmtMoney }, marginCol,
        ]}
        csv={[
          { title: 'Продукт', value: (r) => r.name }, { title: 'Количество', value: (r) => r.quantity },
          { title: 'Ед.', value: (r) => r.unit_code }, { title: 'Выручка', value: (r) => r.revenue },
          { title: 'Себестоимость', value: (r) => r.cost }, { title: 'Маржа', value: (r) => r.margin },
          { title: 'Маржа, %', value: (r) => r.margin_percent },
        ]} />
      <ReportTable<ClientSales> title="По клиентам" filename={`продажи_по_клиентам_${suffix}`} rowKey="client" rows={data?.by_client}
        columns={[
          { title: 'Клиент', dataIndex: 'name' },
          { title: 'Тип', dataIndex: 'kind', render: (k: string) => <StatusTag map={CLIENT_KIND} value={k} /> },
          { title: 'Выручка', dataIndex: 'revenue', align: 'right', render: fmtMoney },
          { title: 'Маржа', dataIndex: 'margin', align: 'right', render: fmtMoney }, marginCol,
        ]}
        csv={[
          { title: 'Клиент', value: (r) => r.name }, { title: 'Тип', value: (r) => CLIENT_KIND[r.kind]?.label },
          { title: 'Выручка', value: (r) => r.revenue }, { title: 'Себестоимость', value: (r) => r.cost },
          { title: 'Маржа', value: (r) => r.margin }, { title: 'Маржа, %', value: (r) => r.margin_percent },
        ]} />
    </Space>
  )
}

function ProductionTab({ params }: { params: Record<string, string> }) {
  const { data } = useReport<ProductionReport>('/reports/production/', params, true)
  const suffix = `${params.date_from}_${params.date_to}`
  return (
    <ReportTable<ProductionOutput> title="Выпуск и брак (завершённые задания)" filename={`выпуск_и_брак_${suffix}`} rowKey="product"
      rows={data?.output}
      columns={[
        { title: 'Цех', dataIndex: 'department_name' },
        { title: 'Продукт', dataIndex: 'name' },
        { title: 'Заданий', dataIndex: 'tasks', align: 'right' },
        { title: 'Выпуск', align: 'right', render: (_, r) => fmtQty(r.output, r.unit_code) },
        { title: 'Брак', align: 'right', render: (_, r) => fmtQty(r.defect, r.unit_code) },
        { title: 'Брак, %', dataIndex: 'defect_percent', align: 'right' },
        { title: 'Сырьё, ₸', dataIndex: 'raw_cost', align: 'right', render: fmtMoney },
      ]}
      csv={[
        { title: 'Цех', value: (r) => r.department_name }, { title: 'Продукт', value: (r) => r.name },
        { title: 'Заданий', value: (r) => r.tasks }, { title: 'Выпуск', value: (r) => r.output },
        { title: 'Брак', value: (r) => r.defect }, { title: 'Брак, %', value: (r) => r.defect_percent },
        { title: 'Стоимость сырья', value: (r) => r.raw_cost },
      ]} />
  )
}

function StockTab() {
  const { data } = useReport<StockReport>('/reports/stock/', {}, true)
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}><StatTile label="Сырьё по себестоимости" value={fmtMoney(data?.raw_value)} /></Col>
        <Col xs={24} sm={8}><StatTile label="Готовая продукция" value={fmtMoney(data?.product_value)} /></Col>
        <Col xs={24} sm={8}><StatTile label="Из них просрочено" value={fmtMoney(data?.expired_value)} alert={Number(data?.expired_value) > 0} /></Col>
      </Row>
      <ReportTable<StockValuation> title="Оценка запасов (Σ остаток партии × её себестоимость)" filename="оценка_запасов" rowKey="item"
        rows={data?.valuation}
        columns={[
          { title: 'Артикул', dataIndex: 'code', width: 110 },
          { title: 'Номенклатура', dataIndex: 'name' },
          { title: 'Остаток', align: 'right', render: (_, r) => fmtQty(r.quantity, r.unit_code) },
          { title: 'Годно', align: 'right', render: (_, r) => fmtQty(r.available, r.unit_code) },
          { title: 'Стоимость', dataIndex: 'value', align: 'right', render: fmtMoney },
        ]}
        csv={[
          { title: 'Артикул', value: (r) => r.code }, { title: 'Номенклатура', value: (r) => r.name },
          { title: 'Тип', value: (r) => (r.kind === 'raw' ? 'Сырьё' : 'Продукция') }, { title: 'Ед.', value: (r) => r.unit_code },
          { title: 'Остаток', value: (r) => r.quantity }, { title: 'Годно', value: (r) => r.available },
          { title: 'Стоимость', value: (r) => r.value },
        ]} />
      <Card size="small" title="Партии с истекающим и истёкшим сроком">
        <Table rowKey="lot" size="small" dataSource={data?.expiring} pagination={{ pageSize: 20, hideOnSinglePage: true }} columns={[
          { title: 'Партия', render: (_, r) => <Link to={`/trace/${r.lot}`}>{r.number}</Link> },
          { title: 'Номенклатура', dataIndex: 'name' },
          { title: 'Остаток', align: 'right', render: (_, r) => fmtQty(r.balance, r.unit_code) },
          { title: 'Дней осталось', dataIndex: 'days_left', align: 'right' },
          { title: 'Стоимость', dataIndex: 'value', align: 'right', render: fmtMoney },
        ]} />
      </Card>
    </Space>
  )
}

/** Отчёты с выгрузкой в CSV. Фильтр периода — один для всех вкладок. */
export default function Analytics() {
  const { can } = useAuth()
  const [period, setPeriod] = useState<Period>(defaultPeriod)
  const params = periodParams(period)
  const tabs = [
    ...(can('sales', 'accountant') ? [{ key: 'sales', label: 'Продажи', children: <SalesTab params={params} /> }] : []),
    ...(can('shop_head', 'technologist', 'accountant') ? [{ key: 'production', label: 'Производство', children: <ProductionTab params={params} /> }] : []),
    ...(can('storekeeper', 'technologist', 'shop_head', 'accountant') ? [{ key: 'stock', label: 'Запасы', children: <StockTab /> }] : []),
  ]
  return (
    <>
      <PeriodFilter value={period} onChange={setPeriod} />
      <Tabs items={tabs} destroyOnHidden />
    </>
  )
}
