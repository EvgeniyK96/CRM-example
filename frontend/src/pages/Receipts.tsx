import { DatePicker, Form, Input, Select } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { toOptions, useList } from '../api/hooks'
import { RECEIPT_STATUS } from '../api/statuses'
import type { Receipt, Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import DocumentList from '../components/DocumentList'
import type { FilterField, FilterPreset } from '../components/filters'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

export default function Receipts() {
  const { can } = useAuth()
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  const supplierOptions = toOptions(suppliers.data, (s) => s.name)
  const fields: FilterField[] = [
    { key: 'supplier', label: 'Поставщик', type: 'select', options: supplierOptions },
    { key: 'date', label: 'Дата приёмки', type: 'dateRange', params: ['date_from', 'date_to'] },
  ]
  const presets: FilterPreset[] = [
    { key: 'drafts', label: 'Черновики', values: () => ({ status: ['draft'] }) },
    { key: 'month', label: 'За этот месяц', values: () => ({ date: [dayjs().startOf('month'), dayjs().endOf('month')] }) },
  ]

  return (
    <DocumentList<Receipt>
      url="/purchasing/receipts/"
      path="/receipts"
      statuses={RECEIPT_STATUS}
      filterFields={fields}
      presets={presets}
      searchPlaceholder="Фильтр + поиск: номер, накладная, поставщик"
      canCreate={can('storekeeper')}
      createTitle="Приёмка без заявки"
      createInitial={{ date: dayjs() }}
      fromForm={(v) => ({ ...v, date: toApiDate(v.date as Dayjs) })}
      createForm={
        <>
          <Form.Item name="supplier" label="Поставщик" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={supplierOptions} />
          </Form.Item>
          <Form.Item name="date" label="Дата приёмки" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="invoice_number" label="Номер накладной поставщика"><Input /></Form.Item>
        </>
      }
      columns={[
        { title: 'Номер', dataIndex: 'number', width: 120 },
        { title: 'Дата', dataIndex: 'date', render: fmtDate },
        { title: 'Поставщик', dataIndex: 'supplier_name' },
        { title: 'Накладная', dataIndex: 'invoice_number' },
        { title: 'Заявка', dataIndex: 'order_number', render: (v) => v ?? '—' },
        { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
        { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={RECEIPT_STATUS} value={s} /> },
      ]}
    />
  )
}
