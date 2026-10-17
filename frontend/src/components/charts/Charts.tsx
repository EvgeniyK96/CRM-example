import { Area, AreaChart, Bar, BarChart, CartesianGrid, LabelList, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartTooltip from './ChartTooltip'
import { CHART, fmtCompact, SERIES } from './theme'

const axisProps = { stroke: CHART.axis, tick: { fill: CHART.muted, fontSize: 11 }, tickLine: false }

/** Одна серия во времени: прямые отрезки 2px (без сглаживания — значения дискретные), дымка 10%, перекрестие. */
export function TrendChart({ data, x, y, format, xFormat, height = 220 }: {
  data: object[]
  x: string
  y: string
  format: (v: number) => string
  xFormat: (v: string) => string
  height?: number
}) {
  const rows = data.map((d) => ({ ...d, [y]: Number((d as Record<string, unknown>)[y]) }))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={rows} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey={x} {...axisProps} tickFormatter={xFormat} minTickGap={24} />
        <YAxis {...axisProps} axisLine={false} tickFormatter={fmtCompact} width={56} />
        <Tooltip cursor={{ stroke: CHART.axis }} content={(p) => <ChartTooltip {...p} format={format} labelFormat={(l) => xFormat(String(l))} />} />
        <Area type="linear" dataKey={y} stroke={SERIES[0]} strokeWidth={2} fill={SERIES[0]} fillOpacity={0.1}
          activeDot={{ r: 5, stroke: CHART.surface, strokeWidth: 2 }} dot={false} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

/** Горизонтальные столбцы одной серии (один цвет — слот 1), значение у конца столбца. */
export function BarList({ data, label, value, format }: {
  data: object[]
  label: string
  value: string
  format: (v: number) => string
}) {
  // Значения приходят строками (Decimal) — для шкалы нужны числа
  const rows = data.map((d) => ({ ...d, [value]: Number((d as Record<string, unknown>)[value]) }))
  return (
    <ResponsiveContainer width="100%" height={rows.length * 36 + 16}>
      <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 72, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={CHART.grid} horizontal={false} />
        <XAxis type="number" hide />
        <YAxis type="category" dataKey={label} {...axisProps} axisLine={false} width={170}
          tick={{ fill: CHART.textSecondary, fontSize: 12 }} />
        <Tooltip cursor={{ fill: CHART.grid, fillOpacity: 0.4 }} content={(p) => <ChartTooltip {...p} format={format} />} />
        <Bar dataKey={value} fill={SERIES[0]} maxBarSize={20} radius={[0, 4, 4, 0]} isAnimationActive={false}>
          <LabelList dataKey={value} position="right" formatter={(v) => format(Number(v))}
            style={{ fill: CHART.textSecondary, fontSize: 11 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

/** Накопительные горизонтальные столбцы (до 3 серий — проверенные слоты 1–3), легенда обязательна. */
export function StackedBars({ data, label, series, format }: {
  data: object[]
  label: string
  series: { key: string; name: string }[]
  format: (v: number) => string
}) {
  return (
    <ResponsiveContainer width="100%" height={data.length * 40 + 56}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={CHART.grid} horizontal={false} />
        <XAxis type="number" {...axisProps} allowDecimals={false} />
        <YAxis type="category" dataKey={label} {...axisProps} axisLine={false} width={170}
          tick={{ fill: CHART.textSecondary, fontSize: 12 }} />
        <Tooltip cursor={{ fill: CHART.grid, fillOpacity: 0.4 }} content={(p) => <ChartTooltip {...p} format={format} />} />
        {/* Текст легенды — цветом текста; цвет серии несёт только значок */}
        <Legend iconType="rect" iconSize={10} wrapperStyle={{ fontSize: 12 }}
          formatter={(value) => <span style={{ color: CHART.textSecondary }}>{value}</span>} />
        {series.map((s, i) => (
          // Зазор 2px цвета фона между сегментами, а не обводка
          <Bar key={s.key} dataKey={s.key} name={s.name} stackId="stack" fill={SERIES[i]} stroke={CHART.surface}
            strokeWidth={2} maxBarSize={22} isAnimationActive={false}
            radius={i === series.length - 1 ? [0, 4, 4, 0] : 0} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
