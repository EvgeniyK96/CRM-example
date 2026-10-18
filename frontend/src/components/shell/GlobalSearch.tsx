import { SearchOutlined } from '@ant-design/icons'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Dropdown, Input, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'

interface Group { type: string; label: string; results: { title: string; subtitle: string; path: string }[] }

/** Поиск по всей системе в шапке: номера документов, клиенты, номенклатура, партии, сотрудники. */
export default function GlobalSearch() {
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)

  // Запрос уходит, когда пользователь перестал печатать
  useEffect(() => {
    const t = setTimeout(() => setQ(text.trim()), 250)
    return () => clearTimeout(t)
  }, [text])

  const { data, isFetching } = useQuery({
    queryKey: ['/reports/search/', q],
    queryFn: async () => (await api.get<Group[]>('/reports/search/', { params: { q } })).data,
    enabled: q.length >= 2,
    placeholderData: keepPreviousData,
  })

  const groups = q.length >= 2 ? data ?? [] : []
  const items = groups.length
    ? groups.map((g) => ({
      type: 'group' as const,
      key: g.type,
      label: g.label,
      children: g.results.map((r) => ({
        key: r.path,
        label: (
          <div style={{ lineHeight: 1.3, padding: '2px 0' }}>
            <div>{r.title}</div>
            <div style={{ fontSize: 12, color: '#898781' }}>{r.subtitle}</div>
          </div>
        ),
      })),
    }))
    : [{ key: 'empty', disabled: true, label: isFetching ? <Spin size="small" /> : 'Ничего не найдено' }]

  const go = (path: string) => {
    setText('')
    setOpen(false)
    navigate(path)
  }

  return (
    <Dropdown
      open={open && q.length >= 2}
      onOpenChange={(next, info) => info.source === 'trigger' && setOpen(next)}
      trigger={['click']}
      menu={{ items, onClick: ({ key }) => key !== 'empty' && go(key), style: { maxHeight: 460, overflow: 'auto', minWidth: 420 } }}
    >
      <Input
        className="shell-search"
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        prefix={<SearchOutlined style={{ color: 'rgba(255,255,255,0.75)' }} />}
        placeholder="Поиск: номер заказа, клиент, продукт, партия…"
        allowClear
        style={{ maxWidth: 480 }}
        aria-label="Глобальный поиск"
      />
    </Dropdown>
  )
}
