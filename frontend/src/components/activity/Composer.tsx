import { SendOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Button, Mentions } from 'antd'
import { useState } from 'react'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'
import type { Person } from '../../api/types'

interface Props {
  placeholder: string
  /** Документ, к которому комментарий; без него — сообщение в ленту */
  target?: { type: string; id: number | string }
}

/** Поле комментария / сообщения: «@» — упомянуть коллегу (придёт уведомление), Ctrl+Enter — отправить. */
export default function Composer({ placeholder, target }: Props) {
  const [text, setText] = useState('')
  const people = useQuery({
    queryKey: ['/activity/people/'],
    queryFn: async () => (await api.get<Person[]>('/activity/people/')).data,
    staleTime: 10 * 60_000,
  })
  const send = useApiAction(
    () => api.post('/activity/', { text, ...(target ? { target: target.type, target_id: target.id } : {}) }),
    { invalidate: ['/activity/'], onSuccess: () => setText('') },
  )
  // Поиск по имени и логину: «@мар» найдёт Марию
  const haystack = new Map(people.data?.map((p) => [p.username, `${p.name} ${p.username}`.toLowerCase()]))
  const submit = () => text.trim() && !send.isPending && send.mutate()

  return (
    <div className="activity-composer">
      <Mentions value={text} onChange={setText} placeholder={`${placeholder} (@ — упомянуть)`} aria-label={placeholder}
        autoSize={{ minRows: 1, maxRows: 8 }} maxLength={4000}
        filterOption={(input, option) => (haystack.get(String(option?.value)) ?? '').includes(input.toLowerCase())}
        options={people.data?.map((p) => ({
          value: p.username,
          label: `${p.name} @${p.username} — ${p.role_display}`,
        }))}
        onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit() } }} />
      <Button type="primary" icon={<SendOutlined />} onClick={submit} loading={send.isPending} disabled={!text.trim()}
        title="Отправить (Ctrl+Enter)">
        Отправить
      </Button>
    </div>
  )
}
