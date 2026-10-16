import { Tag } from 'antd'
import type { StatusInfo } from '../api/statuses'

export default function StatusTag({ map, value }: { map: Record<string, StatusInfo>; value: string }) {
  const s = map[value] ?? { color: 'default', label: value }
  return <Tag color={s.color}>{s.label}</Tag>
}
