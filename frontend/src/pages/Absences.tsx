import { DatePicker, Form, Input, Select } from 'antd'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { toOptions, useList } from '../api/hooks'
import { ABSENCE_KIND, statusOptions } from '../api/statuses'
import type { Absence, Employee } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'
import StatusTag from '../components/StatusTag'
import { fmtDate, fromApiDate, toApiDate } from '../utils/format'

export default function Absences() {
  const { can } = useAuth()
  const [kind, setKind] = useState<string>()
  const employees = useList<Employee>('/hr/employees/', { status: 'active' })

  return (
    <CrudPage<Absence>
      url="/hr/absences/"
      entity="Отсутствие"
      canEdit={can('hr')}
      params={{ kind }}
      searchPlaceholder="Сотрудник, комментарий"
      toolbar={<Select allowClear placeholder="Вид" style={{ width: 200 }} value={kind} onChange={setKind} options={statusOptions(ABSENCE_KIND)} />}
      initialValues={{ kind: 'vacation' }}
      toForm={(a) => ({ ...a, period: [fromApiDate(a.date_from), fromApiDate(a.date_to)] })}
      fromForm={({ period, ...v }) => {
        const [from, to] = period as [Dayjs, Dayjs]
        return { ...v, date_from: toApiDate(from), date_to: toApiDate(to) }
      }}
      columns={[
        { title: 'Сотрудник', dataIndex: 'employee_name' },
        { title: 'Подразделение', dataIndex: 'department_name' },
        { title: 'Вид', dataIndex: 'kind', render: (k: string) => <StatusTag map={ABSENCE_KIND} value={k} /> },
        { title: 'Период', render: (_, a) => `${fmtDate(a.date_from)} — ${fmtDate(a.date_to)}` },
        { title: 'Дней', dataIndex: 'days', align: 'right', width: 80 },
        { title: 'Комментарий', dataIndex: 'comment' },
      ]}
      form={
        <>
          <Form.Item name="employee" label="Сотрудник" rules={[{ required: true }]}>
            <Select showSearch={{ optionFilterProp: 'label' }} options={toOptions(employees.data, (e) => `${e.full_name} — ${e.department_name}`)} />
          </Form.Item>
          <Form.Item name="kind" label="Вид" rules={[{ required: true }]}><Select options={statusOptions(ABSENCE_KIND)} /></Form.Item>
          <Form.Item name="period" label="Период" rules={[{ required: true }]}><DatePicker.RangePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="comment" label="Комментарий"><Input /></Form.Item>
        </>
      }
    />
  )
}
