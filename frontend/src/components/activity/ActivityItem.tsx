import { DeleteOutlined, FileAddOutlined, SettingOutlined, SwapOutlined } from '@ant-design/icons'
import { Avatar, Button, Popconfirm, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'
import { ACTIVITY_TARGET_STATUS } from '../../api/statuses'
import type { Activity } from '../../api/types'
import { ACCENT } from '../../theme'
import { fmtAgo, fmtDateTime } from '../../utils/format'
import StatusTag from '../StatusTag'

const initials = (name: string) => name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase()

/** Запись ленты. withTarget — показывать, к какому документу относится (в общей ленте). */
export default function ActivityItem({ item, withTarget }: { item: Activity; withTarget?: boolean }) {
  const remove = useApiAction(() => api.delete(`/activity/${item.id}/`), { success: 'Удалено', invalidate: ['/activity/'] })
  const statuses = item.target ? ACTIVITY_TARGET_STATUS[item.target.type] : undefined
  const isEvent = item.kind === 'created' || item.kind === 'status'
  const target = item.target && (item.target.path
    ? <Link to={item.target.path}>{item.target.title}</Link>
    : <span className="activity-muted">{item.target.title}</span>)

  return (
    <article className={`activity-item activity-${item.kind}`}>
      {item.author_name
        ? <Avatar style={{ background: ACCENT, flex: 'none' }} aria-hidden>{initials(item.author_name)}</Avatar>
        : <Avatar style={{ background: '#8c8c8c', flex: 'none' }} icon={<SettingOutlined />} aria-hidden />}
      <div className="activity-body">
        <header className="activity-head">
          <span className="activity-author">{item.author_name ?? 'Система'}</span>
          {item.author_role && <span className="activity-muted">{item.author_role}</span>}
          <Tooltip title={fmtDateTime(item.created_at)}>
            <time className="activity-muted" dateTime={item.created_at}>{fmtAgo(item.created_at)}</time>
          </Tooltip>
          {item.can_delete && (
            <Popconfirm title="Удалить запись?" okText="Удалить" cancelText="Нет" onConfirm={() => remove.mutate()}>
              <Button type="text" size="small" className="activity-delete" icon={<DeleteOutlined />} aria-label="Удалить запись" />
            </Popconfirm>
          )}
        </header>
        {isEvent ? (
          <div className="activity-event">
            {item.kind === 'created' ? <FileAddOutlined aria-hidden /> : <SwapOutlined aria-hidden />}
            {item.kind === 'created' ? (
              <span>{withTarget ? <>Создан документ {target}</> : 'Документ создан'}</span>
            ) : (
              <span>
                {withTarget && <>{target}: </>}
                {statuses ? (
                  <><StatusTag map={statuses} value={item.old_status} /> → <StatusTag map={statuses} value={item.new_status} /></>
                ) : item.text}
              </span>
            )}
          </div>
        ) : (
          <>
            {withTarget && item.kind === 'comment' && <div className="activity-muted activity-about">Комментарий к {target}</div>}
            <div className="activity-text">{item.text}</div>
          </>
        )}
      </div>
    </article>
  )
}
