import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Input, Modal, Select, Table, Tag, message } from 'antd'
import { useState } from 'react'
import { api, type Page } from '../api/client'
import { ROLE_LABELS, type User } from '../api/types'

export default function Users() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const users = useQuery({
    queryKey: ['users'],
    queryFn: async () => (await api.get<Page<User>>('/accounts/users/', { params: { page_size: 200 } })).data,
  })

  const create = useMutation({
    mutationFn: (v: object) => api.post('/accounts/users/', v),
    onSuccess: () => {
      message.success('Пользователь создан')
      qc.invalidateQueries({ queryKey: ['users'] })
      setOpen(false)
      form.resetFields()
    },
    onError: () => message.error('Не удалось создать (логин занят или пароль слишком простой)'),
  })

  return (
    <>
      <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: 16 }} onClick={() => setOpen(true)}>Добавить</Button>
      <Table
        rowKey="id"
        loading={users.isLoading}
        dataSource={users.data?.results}
        columns={[
          { title: 'Логин', dataIndex: 'username' },
          { title: 'Имя', render: (_, u) => `${u.last_name} ${u.first_name}`.trim() },
          { title: 'Роль', dataIndex: 'role_display' },
          { title: 'Активен', dataIndex: 'is_active', render: (a: boolean) => <Tag color={a ? 'green' : 'red'}>{a ? 'Да' : 'Нет'}</Tag> },
        ]}
      />
      <Modal title="Новый пользователь" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} confirmLoading={create.isPending} okText="Создать">
        <Form form={form} layout="vertical" onFinish={(v) => create.mutate(v)}>
          <Form.Item name="username" label="Логин" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 8 }]}><Input.Password /></Form.Item>
          <Form.Item name="first_name" label="Имя"><Input /></Form.Item>
          <Form.Item name="last_name" label="Фамилия"><Input /></Form.Item>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
