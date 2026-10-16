import type { RecipeStatus } from '../api/types'

export const RECIPE_STATUS: Record<RecipeStatus, { color: string; label: string }> = {
  draft: { color: 'blue', label: 'Черновик' },
  active: { color: 'green', label: 'Активна' },
  archived: { color: 'default', label: 'В архиве' },
}
