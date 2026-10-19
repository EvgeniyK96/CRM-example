import { BellOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Empty, Popover, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Page } from '../../api/client'
import type { AppNotification } from '../../api/types'
import { fmtAgo } from '../../utils/format'

const URL = '/activity/notifications/'
const POLL_MS = 30_000
const TITLE = document.title

/** Что произошло — одной строкой. */
function what(n: AppNotification) {
  const a = n.activity
  const target = a.target?.title
  if (a.kind === 'comment') return <>Комментарий к <b>{target}</b></>
  if (a.kind === 'post') return <>Сообщение в ленте</>
  if (a.kind === 'created') return <>Новый документ <b>{target}</b></>
  return <><b>{target}</b>: {a.text}</>
}

const REASON: Record<AppNotification['reason'], string> = {
  mention: 'Вас упомянули',
  participant: 'Ваш документ',
  role: '',
}

/** Колокольчик в шапке: число непрочитанных (опрос раз в 30 с), последние уведомления, переход к документу. */
export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const count = useQuery({
    queryKey: [URL, 'count'],
    queryFn: async () => (await api.get<{ unread: number }>(`${URL}count/`)).data.unread,
    refetchInterval: POLL_MS,
  })
  const list = useQuery({
    queryKey: [URL, 'list'],
    queryFn: async () => (await api.get<Page<AppNotification>>(URL, { params: { page_size: 20 } })).data.results,
    enabled: open,
  })
  const unread = count.data ?? 0

  // Новые уведомления видны и на вкладке браузера: «(3) CRM — …»
  useEffect(() => {
    document.title = unread ? `(${unread}) ${TITLE}` : TITLE
  }, [unread])

  // Пришло новое — обновим и ленту с таймлайнами, чтобы комментарий был виден сразу
  const [seen, setSeen] = useState(unread)
  if (unread !== seen) {
    if (unread > seen) qc.invalidateQueries({ queryKey: ['/activity/'] })
    setSeen(unread)
  }

  const refresh = () => qc.invalidateQueries({ queryKey: [URL] })
  const openItem = (n: AppNotification) => {
    setOpen(false)
    if (!n.is_read) api.post(`${URL}${n.id}/read/`).then(refresh)
    navigate(n.activity.target?.path ?? '/feed')
  }
  const readAll = async () => {
    await api.post(`${URL}read_all/`)
    refresh()
  }

  const content = (
    <div className="bell-panel">
      <div className="bell-head">
        <b>Уведомления</b>
        {unread > 0 && <Button type="link" size="small" onClick={readAll}>Прочитать все</Button>}
      </div>
      {list.isLoading ? <Spin style={{ display: 'block', margin: 24 }} /> : list.data?.length ? (
        <ul className="bell-list">
          {list.data.map((n) => (
            <li key={n.id}>
              <button type="button" className={`bell-item${n.is_read ? '' : ' bell-unread'}`} onClick={() => openItem(n)}>
                <span className="bell-reason">
                  {n.activity.author_name ?? 'Система'}{(n.text || REASON[n.reason]) && ` · ${n.text || REASON[n.reason]}`}
                </span>
                <span className="bell-what">{what(n)}</span>
                {(n.activity.kind === 'comment' || n.activity.kind === 'post') && <span className="bell-quote">{n.activity.text}</span>}
                <span className="bell-time">{fmtAgo(n.created_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Уведомлений нет" />}
    </div>
  )

  return (
    <Popover open={open} onOpenChange={(o) => { setOpen(o); if (o) list.refetch() }} trigger="click" placement="bottomRight"
      arrow={false} content={content}>
      <button type="button" className="shell-bell" aria-label={unread ? `Уведомления: ${unread} непрочитанных` : 'Уведомления'}>
        <Badge count={unread} size="small" overflowCount={99} offset={[2, -2]}>
          <BellOutlined style={{ fontSize: 20, color: '#fff' }} />
        </Badge>
      </button>
    </Popover>
  )
}
