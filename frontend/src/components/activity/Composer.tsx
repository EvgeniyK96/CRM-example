import { SendOutlined } from '@ant-design/icons'
import { Button, Input } from 'antd'
import { useState } from 'react'
import { api } from '../../api/client'
import { useApiAction } from '../../api/hooks'

interface Props {
  placeholder: string
  /** Документ, к которому комментарий; без него — сообщение в ленту */
  target?: { type: string; id: number | string }
}

/** Поле комментария / сообщения: Ctrl+Enter — отправить. */
export default function Composer({ placeholder, target }: Props) {
  const [text, setText] = useState('')
  const send = useApiAction(
    () => api.post('/activity/', { text, ...(target ? { target: target.type, target_id: target.id } : {}) }),
    { invalidate: ['/activity/'], onSuccess: () => setText('') },
  )
  const submit = () => text.trim() && !send.isPending && send.mutate()

  return (
    <div className="activity-composer">
      <Input.TextArea value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder} aria-label={placeholder}
        autoSize={{ minRows: 1, maxRows: 8 }} maxLength={4000}
        onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit() } }} />
      <Button type="primary" icon={<SendOutlined />} onClick={submit} loading={send.isPending} disabled={!text.trim()}
        title="Отправить (Ctrl+Enter)">
        Отправить
      </Button>
    </div>
  )
}
