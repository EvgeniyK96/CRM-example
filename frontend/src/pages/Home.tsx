import { Typography } from 'antd'
import { useAuth } from '../auth/AuthContext'

export default function Home() {
  const { user } = useAuth()
  return <Typography.Title level={3}>Добро пожаловать, {user?.first_name || user?.username}</Typography.Title>
}
