import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, DatePicker, Form, Input, Modal, Select, Table, Tag, message } from 'antd'
import dayjs from 'dayjs'
import { useState } from 'react'
import { api, type Page } from '../api/client'
import type { Department, Employee, Position } from '../api/types'
import { useAuth } from '../auth/AuthContext'

const STATUS = { active: ['green', 'Работает'], leave: ['orange', 'В отпуске'], fired: ['red', 'Уволен'] } as const

const useList = <T,>(key: string, url: string, params: object = {}) =>
  useQuery({ queryKey: [key, params], queryFn: async () => (await api.get<Page<T>>(url, { params: { page_size: 200, ...params } })).data })

export default function Employees() {
  const { can } = useAuth()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const employees = useList<Employee>('employees', '/hr/employees/', { search })
  const departments = useList<Department>('departments', '/hr/departments/')
  const positions = useList<Position>('positions', '/hr/positions/')

  const create = useMutation({
    mutationFn: (v: object) => api.post('/hr/employees/', v),
    onSuccess: () => {
      message.success('Сотрудник добавлен')
      qc.invalidateQueries({ queryKey: ['employees'] })
      setOpen(false)
      form.resetFields()
    },
    onError: () => message.error('Не удалось сохранить'),
  })

  const submit = (v: { birth_date?: dayjs.Dayjs; hire_date: dayjs.Dayjs }) =>
    create.mutate({
      ...v,
      birth_date: v.birth_date?.format('YYYY-MM-DD') ?? null,
      hire_date: v.hire_date.format('YYYY-MM-DD'),
    })

  return (
    <>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Input.Search placeholder="Поиск по ФИО, телефону, ИИН" allowClear onSearch={setSearch} style={{ maxWidth: 360 }} />
        {can('hr') && <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Добавить</Button>}
      </div>
      <Table
        rowKey="id"
        loading={employees.isLoading}
        dataSource={employees.data?.results}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: 'ФИО', dataIndex: 'full_name' },
          { title: 'Подразделение', dataIndex: 'department_name' },
          { title: 'Должность', dataIndex: 'position_name' },
          { title: 'Принят', dataIndex: 'hire_date' },
          { title: 'Телефон', dataIndex: 'phone' },
          { title: 'Статус', dataIndex: 'status', render: (s: Employee['status']) => <Tag color={STATUS[s][0]}>{STATUS[s][1]}</Tag> },
        ]}
      />
      <Modal title="Новый сотрудник" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} confirmLoading={create.isPending} okText="Сохранить">
        <Form form={form} layout="vertical" onFinish={submit} initialValues={{ hire_date: dayjs() }}>
          <Form.Item name="last_name" label="Фамилия" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="first_name" label="Имя" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="middle_name" label="Отчество"><Input /></Form.Item>
          <Form.Item name="birth_date" label="Дата рождения"><DatePicker style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="phone" label="Телефон"><Input /></Form.Item>
          <Form.Item name="department" label="Подразделение" rules={[{ required: true }]}>
            <Select options={departments.data?.results.map((d) => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="position" label="Должность" rules={[{ required: true }]}>
            <Select options={positions.data?.results.map((p) => ({ value: p.id, label: p.name }))} />
          </Form.Item>
          <Form.Item name="hire_date" label="Дата приёма" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}
