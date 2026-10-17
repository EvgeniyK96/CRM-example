import { useQuery } from '@tanstack/react-query'
import { Card, Col, DatePicker, Descriptions, Row, Select, Statistic, Table, Tabs, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useList } from '../api/hooks'
import { entrySourcePath } from '../api/statuses'
import type { Account, AccountCard, Payables, ProfitLoss, TrialBalance, TrialBalanceRow } from '../api/types'
import { fmtDate, fmtMoney } from '../utils/format'

type Period = [Dayjs, Dayjs]

function useReport<T>(url: string, params: Record<string, unknown>, enabled = true) {
  return useQuery({
    queryKey: [url, params],
    queryFn: async () => (await api.get<T>(url, { params })).data,
    enabled,
  })
}

const periodParams = ([from, to]: Period) => ({ date_from: from.format('YYYY-MM-DD'), date_to: to.format('YYYY-MM-DD') })
const money = (v: string | null | undefined) => (Number(v) ? fmtMoney(v) : '')

function ProfitLossTab({ period }: { period: Period }) {
  const { data } = useReport<ProfitLoss>('/accounting/reports/profit-loss/', periodParams(period))
  if (!data) return <Card loading />
  const negative = Number(data.net_profit) < 0
  return (
    <>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col><Statistic title="Выручка" value={fmtMoney(data.revenue)} /></Col>
        <Col><Statistic title="Валовая прибыль" value={fmtMoney(data.gross_profit)}
          suffix={data.gross_margin != null ? <Typography.Text type="secondary"> ({data.gross_margin}%)</Typography.Text> : null} /></Col>
        <Col><Statistic title={negative ? 'Чистый убыток' : 'Чистая прибыль'} value={fmtMoney(data.net_profit)}
          styles={{ content: { color: negative ? '#cf1322' : '#3f8600' } }} /></Col>
      </Row>
      <Descriptions bordered size="small" column={1} style={{ maxWidth: 560 }} items={[
        { label: 'Доход от реализации (6010)', children: fmtMoney(data.revenue) },
        { label: 'Себестоимость реализации (7010)', children: `− ${fmtMoney(data.cost_of_sales)}` },
        { label: <b>Валовая прибыль</b>, children: <b>{fmtMoney(data.gross_profit)}</b> },
        { label: 'Административные расходы (7210)', children: `− ${fmtMoney(data.admin_expenses)}` },
        { label: 'Прочие расходы: брак, порча (7470)', children: `− ${fmtMoney(data.other_expenses)}` },
        { label: <b>Чистая прибыль (убыток)</b>, children: <b>{fmtMoney(data.net_profit)}</b> },
      ]} />
    </>
  )
}

function TrialBalanceTab({ period, onAccount }: { period: Period; onAccount: (id: number) => void }) {
  const { data, isLoading } = useReport<TrialBalance>('/accounting/reports/trial-balance/', periodParams(period))
  const t = data?.totals ?? {}
  const pair = (prefix: 'opening' | 'turnover' | 'closing', title: string) => ({
    title,
    children: [
      { title: 'Дебет', dataIndex: `${prefix}_debit`, align: 'right' as const, render: money },
      { title: 'Кредит', dataIndex: `${prefix}_credit`, align: 'right' as const, render: money },
    ],
  })
  return (
    <Table<TrialBalanceRow> rowKey="account" size="small" bordered pagination={false} loading={isLoading} dataSource={data?.rows}
      onRow={(r) => ({ onClick: () => onAccount(r.account), style: { cursor: 'pointer' } })}
      columns={[
        { title: 'Счёт', width: 300, render: (_, r) => <><b>{r.code}</b> {r.name}</> },
        pair('opening', 'Сальдо на начало'), pair('turnover', 'Обороты за период'), pair('closing', 'Сальдо на конец'),
      ]}
      summary={() => (
        <Table.Summary.Row style={{ fontWeight: 600 }}>
          <Table.Summary.Cell index={0}>Итого</Table.Summary.Cell>
          {(['opening_debit', 'opening_credit', 'turnover_debit', 'turnover_credit', 'closing_debit', 'closing_credit'] as const).map((k, i) => (
            <Table.Summary.Cell key={k} index={i + 1} align="right">{fmtMoney(t[k] ?? 0)}</Table.Summary.Cell>
          ))}
        </Table.Summary.Row>
      )} />
  )
}

function AccountCardTab({ period, account, setAccount }: { period: Period; account?: number; setAccount: (id?: number) => void }) {
  const accounts = useList<Account>('/accounting/accounts/')
  const { data, isLoading } = useReport<AccountCard>('/accounting/reports/account-card/', { ...periodParams(period), account }, !!account)
  return (
    <>
      <Select showSearch={{ optionFilterProp: 'label' }} placeholder="Выберите счёт" style={{ width: 360, marginBottom: 12 }}
        value={account} onChange={setAccount} options={toOptions(accounts.data, (a) => `${a.code} ${a.name}`)} />
      {data && (
        <>
          <Typography.Paragraph>Сальдо на начало: <b>{fmtMoney(data.opening)}</b> · на конец: <b>{fmtMoney(data.closing)}</b>
            <Typography.Text type="secondary"> (плюс — дебетовое, минус — кредитовое)</Typography.Text></Typography.Paragraph>
          <Table rowKey={(r) => `${r.entry}-${r.corr_account}-${r.balance}`} size="small" pagination={{ pageSize: 50, hideOnSinglePage: true }}
            loading={isLoading} dataSource={data.rows} columns={[
              { title: 'Дата', dataIndex: 'date', render: fmtDate, width: 100 },
              {
                title: 'Операция',
                render: (_, r) => {
                  const path = entrySourcePath(r.source_type, r.source_id)
                  return path ? <Link to={path}>{r.description}</Link> : r.description
                },
              },
              { title: 'Корр. счёт', dataIndex: 'corr_account' },
              { title: 'Контрагент', dataIndex: 'counterparty', render: (v) => v ?? '' },
              { title: 'Дебет', dataIndex: 'debit', align: 'right', render: money },
              { title: 'Кредит', dataIndex: 'credit', align: 'right', render: money },
              { title: 'Сальдо', dataIndex: 'balance', align: 'right', render: fmtMoney },
            ]} />
        </>
      )}
    </>
  )
}

function PayablesTab() {
  const { data, isLoading } = useReport<Payables>('/accounting/reports/payables/', {})
  return (
    <>
      <Statistic title="Долг поставщикам" value={fmtMoney(data?.total_debt)} style={{ marginBottom: 12 }} />
      <Table rowKey="supplier" size="small" pagination={false} loading={isLoading} dataSource={data?.rows} columns={[
        { title: 'Поставщик', dataIndex: 'supplier_name' },
        { title: 'Поставлено', dataIndex: 'received', align: 'right', render: fmtMoney },
        { title: 'Оплачено', dataIndex: 'paid', align: 'right', render: fmtMoney },
        { title: 'Долг', dataIndex: 'debt', align: 'right', render: (v: string) => <b>{fmtMoney(v)}</b> },
      ]} />
    </>
  )
}

export default function FinanceReports() {
  const [period, setPeriod] = useState<Period>([dayjs().startOf('month'), dayjs()])
  const [tab, setTab] = useState('pnl')
  const [account, setAccount] = useState<number>()

  const openCard = (id: number) => {
    setAccount(id)
    setTab('card')
  }

  return (
    <Card>
      <div style={{ marginBottom: 8 }}>
        Период:{' '}
        <DatePicker.RangePicker value={period} allowClear={false} onChange={(v) => v?.[0] && v[1] && setPeriod([v[0], v[1]])} />
      </div>
      <Tabs activeKey={tab} onChange={setTab} items={[
        { key: 'pnl', label: 'Прибыли и убытки', children: <ProfitLossTab period={period} /> },
        { key: 'tb', label: 'Оборотно-сальдовая ведомость', children: <TrialBalanceTab period={period} onAccount={openCard} /> },
        { key: 'card', label: 'Карточка счёта', children: <AccountCardTab period={period} account={account} setAccount={setAccount} /> },
        { key: 'payables', label: 'Кредиторская задолженность', children: <PayablesTab /> },
      ]} />
    </Card>
  )
}
