import { useInfiniteQuery } from '@tanstack/react-query'
import { Button, Empty, Segmented, Skeleton, Typography } from 'antd'
import { useState } from 'react'
import { api, type Page } from '../api/client'
import type { Activity } from '../api/types'
import ActivityItem from '../components/activity/ActivityItem'
import Composer from '../components/activity/Composer'

type Show = 'all' | 'talk' | 'events'

const KINDS: Record<Show, string[] | undefined> = {
  all: undefined,
  talk: ['post', 'comment'],
  events: ['created', 'status'],
}

const PAGE_SIZE = 30
const REFRESH_MS = 30_000

/** Живая лента: сообщения, комментарии и события документов всей фабрики; обновляется сама раз в 30 секунд. */
export default function Feed() {
  const [show, setShow] = useState<Show>('all')
  const feed = useInfiniteQuery({
    queryKey: ['/activity/', 'feed', show],
    queryFn: async ({ pageParam }) =>
      (await api.get<Page<Activity>>('/activity/', { params: { kind: KINDS[show], page: pageParam, page_size: PAGE_SIZE } })).data,
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
    refetchInterval: REFRESH_MS,
    refetchIntervalInBackground: false,
  })
  const items = feed.data?.pages.flatMap((p) => p.results) ?? []

  return (
    <div className="feed">
      <Composer placeholder="Написать сообщение всем сотрудникам…" />
      <div className="feed-toolbar">
        <Segmented<Show> value={show} onChange={setShow} options={[
          { value: 'all', label: 'Всё' },
          { value: 'talk', label: 'Сообщения и комментарии' },
          { value: 'events', label: 'События документов' },
        ]} />
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>Обновляется автоматически</Typography.Text>
      </div>
      {feed.isLoading ? <Skeleton active avatar paragraph={{ rows: 3 }} /> : items.length ? (
        <div className="activity-list feed-list" aria-live="polite">
          {items.map((a) => <ActivityItem key={a.id} item={a} withTarget />)}
        </div>
      ) : <Empty description="В ленте пока пусто" />}
      {feed.hasNextPage && (
        <Button block onClick={() => feed.fetchNextPage()} loading={feed.isFetchingNextPage} style={{ marginTop: 12 }}>
          Показать ещё
        </Button>
      )}
    </div>
  )
}
