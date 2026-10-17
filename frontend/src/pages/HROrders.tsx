import { Button, DatePicker, Form, Input, InputNumber, Modal, Radio, Select, Table } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../api/client'
import { toOptions, useApiAction, useList } from '../api/hooks'
import { HR_ORDER_KIND } from '../api/statuses'
import type { Department, Employee, HROrder, Position } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import StatusTag from '../components/StatusTag'
import { fmtDate, fmtMoney, toApiDate } from '../utils/format'

const URL = '/hr/orders/'

function OrderModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form] = Form.useForm()
  const kind = Form.useWatch('kind', form)
  const employees = useList<Employee>('/hr/employees/', { status: 'active' }, open)
  const departments = useList<Department>('/hr/departments/', { is_active: true }, open)
  const positions = useList<Position>('/hr/positions/', {}, open)
  const save = useApiAction((v: object) => api.post(URL, v), { success: 'Приказ оформлен', invalidate: 'all', onSuccess: onClose })

  return (
    <Modal title="Новый кадровый приказ" open={open} onCancel={onClose} onOk={() => form.submit()} okText="Оформить"
      okButtonProps={{ loading: save.isPending, danger: kind === 'dismissal' }} destroyOnHidden>
      <Form form={form} layout="vertical" preserve={false} initialValues={{ kind: 'transfer', date: dayjs() }}
        onFinish={(v) => save.mutate({ ...v, date: toApiDate(v.date as Dayjs) })}>
        <Form.Item name="kind" label="Вид приказа">
          <Radio.Group optionType="button" options={[
            { value: 'transfer', label: 'Перевод' }, { value: 'salary', label: 'Изменение оклада' }, { value: 'dismissal', label: 'Увольнение' },
          ]} />
        </Form.Item>
        <Form.Item name="employee" label="Сотрудник" rules={[{ required: true }]}>
          <Select showSearch={{ optionFilterProp: 'label' }}
            options={toOptions(employees.data, (e) => `${e.full_name} — ${e.department_name}, ${e.position_name}, ${fmtMoney(e.salary)}`)} />
        </Form.Item>
        <Form.Item name="date" label="Дата вступления в силу" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
        {kind === 'transfer' && (
          <>
            <Form.Item name="to_department" label="В подразделение"><Select allowClear options={toOptions(departments.data, (d) => d.name)} /></Form.Item>
            <Form.Item name="to_position" label="На должность"><Select allowClear options={toOptions(positions.data, (p) => p.name)} /></Form.Item>
            <Form.Item name="to_salary" label="Новый оклад" extra="Пусто — оклад не меняется">
              <InputNumber min="1" stringMode style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}
        {kind === 'salary' && (
          <Form.Item name="to_salary" label="Новый оклад" rules={[{ required: true }]}><InputNumber min="1" stringMode style={{ width: '100%' }} /></Form.Item>
        )}
        <Form.Item name="reason" label="Основание" extra={kind === 'dismissal' ? 'Учётная запись сотрудника будет заблокирована' : undefined}>
          <Input />
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default function HROrders() {
  const { can } = useAuth()
  const [kind, setKind] = useState<string>()
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const orders = useList<HROrder>(URL, { kind, search })

  const change = (o: HROrder) => {
    const parts = []
    if (o.kind === 'hire') parts.push(`${o.to_department_name}, ${o.to_position_name}, оклад ${fmtMoney(o.to_salary)}`)
    if (o.kind === 'transfer') {
      if (o.from_department_name !== o.to_department_name) parts.push(`${o.from_department_name} → ${o.to_department_name}`)
      if (o.from_position_name !== o.to_position_name) parts.push(`${o.from_position_name} → ${o.to_position_name}`)
    }
    if ((o.kind === 'salary' || o.kind === 'transfer') && o.from_salary !== o.to_salary) {
      parts.push(`оклад ${fmtMoney(o.from_salary)} → ${fmtMoney(o.to_salary)}`)
    }
    return parts.join('; ') || '—'
  }

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Input.Search placeholder="Номер, сотрудник, основание" allowClear onSearch={setSearch} style={{ maxWidth: 280 }} />
        <Select allowClear placeholder="Вид" style={{ width: 200 }} value={kind} onChange={setKind}
          options={Object.entries(HR_ORDER_KIND).map(([value, s]) => ({ value, label: s.label }))} />
        {can('hr') && <Button type="primary" onClick={() => setOpen(true)}>Новый приказ</Button>}
      </div>
      <Table<HROrder> rowKey="id" size="middle" loading={orders.isLoading} dataSource={orders.data}
        pagination={{ pageSize: 30, hideOnSinglePage: true }}
        columns={[
          { title: 'Номер', dataIndex: 'number', width: 110 },
          { title: 'Дата', dataIndex: 'date', render: fmtDate, width: 110 },
          { title: 'Вид', dataIndex: 'kind', render: (k: string) => <StatusTag map={HR_ORDER_KIND} value={k} /> },
          { title: 'Сотрудник', dataIndex: 'employee_name' },
          { title: 'Изменение', render: (_, o) => change(o) },
          { title: 'Основание', dataIndex: 'reason' },
          { title: 'Оформил', dataIndex: 'created_by_name', render: (v) => v ?? '—' },
        ]} />
      <OrderModal open={open} onClose={() => setOpen(false)} />
    </>
  )
}
