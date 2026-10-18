import { isAxiosError } from 'axios'
import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ACCENT, WALLPAPER } from '../theme'

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
    } catch (e) {
      // «Неверный пароль» — только когда сервер так и ответил; иначе показываем настоящую причину
      const status = isAxiosError(e) ? e.response?.status : undefined
      const isJson = isAxiosError(e) && String(e.response?.headers['content-type'] ?? '').includes('json')
      if (status === 401) setError('Неверный логин или пароль')
      else if (!status) setError('Сервер недоступен. Проверьте подключение и адрес API.')
      else if (!isJson || status === 404 || status === 405) setError(`API не отвечает (HTTP ${status}): запросы /api не доходят до бэкенда`)
      else setError(`Ошибка сервера (HTTP ${status})`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: WALLPAPER, padding: 16 }}>
      <Card style={{ width: 380, maxWidth: '100%', boxShadow: '0 12px 40px rgba(0,20,40,0.35)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'center', marginBottom: 8 }}>
          <span className="shell-logo-mark" style={{ background: ACCENT, color: '#fff' }}>Ф</span>
          <Typography.Title level={3} style={{ margin: 0 }}>CRM Фабрика</Typography.Title>
        </div>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>Кондитерская фабрика · учебный проект</Typography.Paragraph>
        {error && <Alert type="error" title={error} style={{ marginBottom: 16 }} />}
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="Логин" rules={[{ required: true }]}><Input autoFocus /></Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>Войти</Button>
        </Form>
      </Card>
    </div>
  )
}
