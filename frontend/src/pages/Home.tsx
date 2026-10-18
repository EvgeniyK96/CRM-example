import { useQuery } from '@tanstack/react-query'
import { Card, Select, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { Payslip } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import Dashboard from '../components/Dashboard'
import PayslipView from '../components/PayslipView'

/** Свои расчётные листки (для сотрудников с учётной записью). */
function MyPayslips() {
  const { data } = useQuery({
    queryKey: ['/payroll/my-payslips/'],
    queryFn: async () => (await api.get<Payslip[]>('/payroll/my-payslips/')).data,
  })
  const [selected, setSelected] = useState<number>()
  if (!data?.length) return null
  const slip = data.find((s) => s.id === selected) ?? data[0]
  return (
    <Card title="Мой расчётный листок" style={{ maxWidth: 640 }}
      extra={<Select value={slip.id} onChange={setSelected} style={{ width: 200 }}
        options={data.map((s) => ({ value: s.id, label: s.period_label }))} />}>
      <PayslipView slip={slip} />
    </Card>
  )
}

export default function Home() {
  const { user } = useAuth()
  return (
    <>
      {user?.department_name && <Typography.Paragraph type="secondary">{user.role_display} · {user.department_name}</Typography.Paragraph>}
      <Dashboard />
      <div style={{ marginTop: 16 }}><MyPayslips /></div>
    </>
  )
}
