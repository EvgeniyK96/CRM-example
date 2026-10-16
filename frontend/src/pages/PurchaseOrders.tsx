import { DatePicker, Form, Input, Select } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { toOptions, useList } from '../api/hooks'
import { PO_STATUS } from '../api/statuses'
import type { PurchaseOrder, Supplier } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import DocumentList from '../components/DocumentList'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

export default function PurchaseOrders() {
  const { can } = useAuth()
  const [supplier, setSupplier] = useState<number>()
  const suppliers = useList<Supplier>('/catalog/suppliers/', { is_active: true })
  const supplierOptions = toOptions(suppliers.data, (s) => s.name)

  return (
    <DocumentList<PurchaseOrder>
      url="/purchasing/orders/"
      path="/purchase-orders"
      statuses={PO_STATUS}
      params={{ supplier }}
      searchPlaceholder="Номер, поставщик"
      filters={<Select allowClear placeholder="Поставщик" style={{ width: 260 }} value={supplier} onChange={setSupplier} options={supplierOptions} />}
      canCreate={can('storekeeper')}
      createTitle="Новая заявка поставщику"
      fromForm={(v) => ({ ...v, expected_date: toApiDate(v.expected_date as Dayjs | undefined) })}
      createForm={
        <>
          <Form.Item name="supplier" label="Поставщик" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={supplierOptions} />
          </Form.Item>
          <Form.Item name="expected_date" label="Ожидаемая дата поставки"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="comment" label="Комментарий"><Input /></Form.Item>
        </>
      }
      columns={[
        { title: 'Номер', dataIndex: 'number', width: 120 },
        { title: 'Поставщик', dataIndex: 'supplier_name' },
        { title: 'Создана', dataIndex: 'created_at', render: fmtDate },
        { title: 'Ожидается', dataIndex: 'expected_date', render: fmtDate },
        { title: 'Сумма', dataIndex: 'total', align: 'right', render: fmtMoney },
        { title: 'Статус', dataIndex: 'status', render: (s: string) => <StatusTag map={PO_STATUS} value={s} /> },
      ]}
    />
  )
}
