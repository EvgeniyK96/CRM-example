import { Button, DatePicker, Form, Input, InputNumber, Modal, Popconfirm, Select, Table, Typography } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { toOptions, useApiAction, useList } from '../api/hooks'
import { ENTRY_SOURCE, entrySourcePath, statusOptions } from '../api/statuses'
import type { Account, JournalEntry } from '../api/types'
import LinesFormList, { type LineColumn } from '../components/LinesFormList'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

const URL = '/accounting/entries/'

function ManualEntryModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()
  const accounts = useList<Account>('/accounting/accounts/', { is_active: true })
  const options = toOptions(accounts.data, (a) => `${a.code} ${a.name}`)
  const save = useApiAction((v: object) => api.post(URL, v), { success: 'Операция записана', invalidate: 'all', onSuccess: onClose })

  const columns: LineColumn[] = [
    { title: 'Дебет', width: 'minmax(200px, 2fr)', render: (i) => <Form.Item name={[i, 'debit']} rules={[{ required: true }]}><Select showSearch={{ optionFilterProp: 'label' }} options={options} /></Form.Item> },
    { title: 'Кредит', width: 'minmax(200px, 2fr)', render: (i) => <Form.Item name={[i, 'credit']} rules={[{ required: true }]}><Select showSearch={{ optionFilterProp: 'label' }} options={options} /></Form.Item> },
    { title: 'Сумма', width: 'minmax(120px, 1fr)', render: (i) => <Form.Item name={[i, 'amount']} rules={[{ required: true }]}><InputNumber min="0.01" stringMode style={{ width: '100%' }} /></Form.Item> },
    { title: 'Комментарий', width: 'minmax(140px, 1fr)', render: (i) => <Form.Item name={[i, 'comment']}><Input /></Form.Item> },
  ]

  return (
    <Modal title="Ручная операция" open={open} onCancel={onClose} onOk={() => form.submit()} okText="Записать" width={900}
      okButtonProps={{ loading: save.isPending }} destroyOnHidden>
      <Typography.Paragraph type="secondary">
        Для операций без документа в системе: взнос учредителя, банковская комиссия, прочие расходы.
        Операции по приёмкам, производству, отгрузкам и платежам формируются автоматически.
      </Typography.Paragraph>
      <Form form={form} layout="vertical" preserve={false} initialValues={{ date: dayjs(), postings: [{}] }}
        onFinish={(v) => save.mutate({ ...v, date: toApiDate(v.date as Dayjs) })}>
        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item name="date" label="Дата" rules={[{ required: true }]}><DatePicker /></Form.Item>
          <Form.Item name="description" label="Содержание" rules={[{ required: true }]} style={{ flex: 1 }}><Input /></Form.Item>
        </div>
        <LinesFormList name="postings" columns={columns} addLabel="Добавить проводку" />
      </Form>
    </Modal>
  )
}

export default function Journal() {
  const [search, setSearch] = useState('')
  const [sources, setSources] = useState<string[]>([])
  const [account, setAccount] = useState<number>()
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>([dayjs().startOf('month'), dayjs()])
  const [manual, setManual] = useState(false)
  const accounts = useList<Account>('/accounting/accounts/')
  const entries = useList<JournalEntry>(URL, {
    search, source_type: sources, account,
    date_from: toApiDate(range?.[0]) ?? undefined, date_to: toApiDate(range?.[1]) ?? undefined,
  })
  const remove = useApiAction((id: number) => api.delete(`${URL}${id}/`), { success: 'Удалено', invalidate: 'all' })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <DatePicker.RangePicker value={range} onChange={(v) => setRange(v)} />
        <Select mode="multiple" allowClear placeholder="Основание" style={{ minWidth: 220 }} value={sources} onChange={setSources}
          options={statusOptions(ENTRY_SOURCE)} />
        <Select allowClear showSearch={{ optionFilterProp: 'label' }} placeholder="Счёт" style={{ width: 280 }} value={account}
          onChange={setAccount} options={toOptions(accounts.data, (a) => `${a.code} ${a.name}`)} />
        <Input.Search placeholder="Содержание" allowClear onSearch={setSearch} style={{ maxWidth: 220 }} />
        <Button type="primary" onClick={() => setManual(true)}>Ручная операция</Button>
      </div>
      <Table<JournalEntry> rowKey="id" size="small" loading={entries.isLoading} dataSource={entries.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        columns={[
          { title: 'Дата', dataIndex: 'date', render: fmtDate, width: 100 },
          {
            title: 'Операция',
            render: (_, e) => {
              const path = entrySourcePath(e.source_type, e.source_id)
              return <>{path ? <Link to={path}>{e.description}</Link> : e.description} <StatusTag map={ENTRY_SOURCE} value={e.source_type} /></>
            },
          },
          {
            title: 'Проводки (Дт — Кт: сумма)',
            render: (_, e) => e.postings.map((p) => (
              <div key={p.id} style={{ whiteSpace: 'nowrap' }}>
                <Typography.Text code>{p.debit_code}</Typography.Text> — <Typography.Text code>{p.credit_code}</Typography.Text>: {fmtMoney(p.amount)}
                {(p.client_name || p.supplier_name) && <Typography.Text type="secondary"> · {p.client_name ?? p.supplier_name}</Typography.Text>}
              </div>
            )),
          },
          { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
          { title: 'Автор', dataIndex: 'created_by_name', render: (v) => v ?? 'система' },
          {
            key: 'del',
            render: (_, e) => e.source_type === 'manual' && (
              <Popconfirm title="Удалить ручную операцию?" onConfirm={() => remove.mutate(e.id)}><Button size="small" danger>Удалить</Button></Popconfirm>
            ),
          },
        ]} />
      <ManualEntryModal open={manual} onClose={() => setManual(false)} />
    </>
  )
}
