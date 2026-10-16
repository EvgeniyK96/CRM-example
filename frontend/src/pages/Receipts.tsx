import { DatePicker, Form, Input, Select } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { toOptions, useList } from '../api/hooks'
import { RECEIPT_STATUS } from '../api/statuses'
import type { Receipt, Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import DocumentList from '../components/DocumentList'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

export default function Receipts() {
  const { can } = useAuth()
  const [supplier, setSupplier] = useState<number>()
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  const supplierOptions = toOptions(suppliers.data, (s) => s.name)

  return (
    <DocumentList<Receipt>
      url="/purchasing/receipts/"
      path="/receipts"
      statuses={RECEIPT_STATUS}
      params={{ supplier }}
      searchPlaceholder="Номер, накладная, поставщик"
      filters={<Select allowClear placeholder="Поставщик" style={{ width: 260 }} value={supplier} onChange={setSupplier} options={supplierOptions} />}
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
