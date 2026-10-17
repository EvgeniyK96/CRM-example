import dayjs, { type Dayjs } from 'dayjs'

export type Period = [Dayjs, Dayjs]

export const PERIOD_PRESETS: Record<string, () => Period> = {
  month: () => [dayjs().startOf('month'), dayjs()],
  d7: () => [dayjs().subtract(6, 'day'), dayjs()],
  d30: () => [dayjs().subtract(29, 'day'), dayjs()],
  d90: () => [dayjs().subtract(89, 'day'), dayjs()],
}

export const defaultPeriod = PERIOD_PRESETS.month

export const periodParams = ([from, to]: Period) => ({ date_from: from.format('YYYY-MM-DD'), date_to: to.format('YYYY-MM-DD') })

export const presetOf = ([from, to]: Period) =>
  Object.entries(PERIOD_PRESETS).find(([, make]) => {
    const [f, t] = make()
    return f.isSame(from, 'day') && t.isSame(to, 'day')
  })?.[0] ?? 'custom'
