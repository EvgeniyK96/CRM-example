import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const onFinish = async (v: { username: string; password: string }) => {
    setBusy(true)
    setError('')
    try {
      await login(v.username, v.password)
      navigate('/')
    } catch {
      setError('Неверный логин или пароль')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#f5f5f5' }}>
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>Кондитерская фабрика</Typography.Title>
        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="Логин" rules={[{ required: true }]}><Input autoFocus /></Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>Войти</Button>
        </Form>
      </Card>
    </div>
  )
}
