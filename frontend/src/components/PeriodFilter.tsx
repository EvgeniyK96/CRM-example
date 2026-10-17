import { DatePicker, Segmented } from 'antd'
import dayjs from 'dayjs'
import { PERIOD_PRESETS, presetOf, type Period } from '../utils/period'

/** Один фильтр периода над всем, что он задаёт: пресеты первыми, произвольный диапазон — следом. */
export default function PeriodFilter({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 }}>
      <Segmented
        value={presetOf(value)}
        onChange={(key) => key !== 'custom' && onChange(PERIOD_PRESETS[key]())}
        options={[
          { value: 'month', label: 'Этот месяц' }, { value: 'd7', label: '7 дней' }, { value: 'd30', label: '30 дней' },
          { value: 'd90', label: '90 дней' }, { value: 'custom', label: 'Период', disabled: true },
        ]}
      />
      <DatePicker.RangePicker value={value} allowClear={false} disabledDate={(d) => d.isAfter(dayjs(), 'day')}
        onChange={(v) => v?.[0] && v[1] && onChange([v[0], v[1]])} />
    </div>
  )
}
