import { DatePicker, Form, Input, InputNumber, Select, Tag } from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { toOptions, useList } from '../api/hooks'
import type { Department, Employee, Position } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import CrudPage from '../components/CrudPage'
import { fmtDate, fmtMoney } from '../utils/format'

const STATUS = { active: ['green', 'Работает'], leave: ['orange', 'В отпуске'], fired: ['red', 'Уволен'] } as const
const DATE_FIELDS = ['birth_date', 'hire_date', 'fire_date'] as const

const toForm = (e: Employee) => ({
  ...e,
  ...Object.fromEntries(DATE_FIELDS.map((f) => [f, e[f] ? dayjs(e[f]) : null])),
})

const fromForm = (v: Record<string, unknown>) => ({
  ...v,
  ...Object.fromEntries(DATE_FIELDS.map((f) => [f, (v[f] as Dayjs | null)?.format('YYYY-MM-DD') ?? null])),
})

export default function Employees() {
  const { can } = useAuth()
  const departments = useList<Department>('/hr/departments/')
  const positions = useList<Position>('/hr/positions/')

  return (
    <CrudPage<Employee>
      url="/hr/employees/"
      entity="Сотрудник"
      canEdit={can('hr')}
      searchPlaceholder="Поиск по ФИО, телефону, ИИН"
      initialValues={{ hire_date: dayjs(), status: 'active' }}
      toForm={toForm}
      fromForm={fromForm}
      columns={[
        { title: 'ФИО', dataIndex: 'full_name' },
        { title: 'Подразделение', dataIndex: 'department_name' },
        { title: 'Должность', dataIndex: 'position_name' },
        { title: 'Оклад', dataIndex: 'salary', align: 'right', render: fmtMoney },
        { title: 'Принят', dataIndex: 'hire_date', render: fmtDate },
        { title: 'Телефон', dataIndex: 'phone' },
        { title: 'Статус', dataIndex: 'status', render: (s: Employee['status']) => <Tag color={STATUS[s][0]}>{STATUS[s][1]}</Tag> },
      ]}
      form={(editing) => {
        // После приёма подразделение, должность, оклад и увольнение меняются кадровым приказом
        const locked = editing ? { disabled: true, extra: 'Меняется кадровым приказом' } : {}
        return (
          <>
            <Form.Item name="last_name" label="Фамилия" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="first_name" label="Имя" rules={[{ required: true }]}><Input /></Form.Item>
            <Form.Item name="middle_name" label="Отчество"><Input /></Form.Item>
            <Form.Item name="birth_date" label="Дата рождения"><DatePicker style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="tax_id" label="ИИН/ИНН"><Input /></Form.Item>
            <Form.Item name="phone" label="Телефон"><Input /></Form.Item>
            <Form.Item name="address" label="Адрес"><Input /></Form.Item>
            <Form.Item name="department" label="Подразделение" rules={[{ required: true }]} extra={locked.extra}>
              <Select disabled={locked.disabled} options={toOptions(departments.data, (d) => d.name)} />
            </Form.Item>
            <Form.Item name="position" label="Должность" rules={[{ required: true }]} extra={locked.extra}>
              <Select disabled={locked.disabled} options={toOptions(positions.data, (p) => p.name)} />
            </Form.Item>
            <Form.Item name="salary" label="Оклад" extra={locked.extra ?? 'Пусто — базовый оклад должности'}>
              <InputNumber disabled={locked.disabled} min="0" stringMode style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="hire_date" label="Дата приёма" rules={[{ required: true }]}>
              <DatePicker disabled={locked.disabled} style={{ width: '100%' }} />
            </Form.Item>
            {editing?.fire_date && (
              <Form.Item name="fire_date" label="Дата увольнения"><DatePicker disabled style={{ width: '100%' }} /></Form.Item>
            )}
          </>
        )
      }}
    />
  )
}
