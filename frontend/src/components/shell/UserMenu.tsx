import { LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { Avatar, Dropdown } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'

/** Профиль в правом углу шапки: инициалы, имя, роль; меню с выходом. */
export default function UserMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null

  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username
  const initials = (user.first_name?.[0] ?? user.username[0]) + (user.last_name?.[0] ?? '')

  return (
    <Dropdown
      trigger={['click']}
      menu={{
        items: [
          { key: 'who', disabled: true, label: <>{user.role_display}{user.department_name ? ` · ${user.department_name}` : ''}</>, icon: <UserOutlined /> },
          { type: 'divider' },
          { key: 'logout', label: 'Выйти', icon: <LogoutOutlined />, danger: true },
        ],
        onClick: ({ key }) => {
          if (key === 'logout') {
            logout()
            navigate('/login')
          }
        },
      }}
    >
      <button type="button" className="shell-user" aria-label="Меню пользователя">
        <Avatar size={34} style={{ background: 'rgba(255,255,255,0.25)', color: '#fff', fontWeight: 600 }}>
          {initials.toUpperCase()}
        </Avatar>
        <span className="shell-user-name">{name}</span>
      </button>
    </Dropdown>
  )
}
