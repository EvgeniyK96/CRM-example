import { useQuery } from '@tanstack/react-query'
import { Card, Empty, Skeleton } from 'antd'
import { api, type Page } from '../../api/client'
import type { Activity } from '../../api/types'
import ActivityItem from './ActivityItem'
import Composer from './Composer'

/**
 * Таймлайн документа: комментарии и события (создан, смена статуса), новые сверху.
 * Обновляется вместе с остальными данными: действия над документом инвалидируют все запросы.
 */
export default function Timeline({ type, id }: { type: string; id: number | string }) {
  const query = useQuery({
    queryKey: ['/activity/', type, String(id)],
    queryFn: async () => (await api.get<Page<Activity>>('/activity/', { params: { target: type, target_id: id, page_size: 200 } })).data.results,
  })

  return (
    <Card size="small" title="История и комментарии">
      <Composer placeholder="Комментарий — увидят все, кто открывает документ" target={{ type, id }} />
      {query.isLoading ? <Skeleton active avatar paragraph={{ rows: 2 }} /> : query.data?.length ? (
        <div className="activity-list">{query.data.map((a) => <ActivityItem key={a.id} item={a} />)}</div>
      ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Пока ничего" />}
    </Card>
  )
}
