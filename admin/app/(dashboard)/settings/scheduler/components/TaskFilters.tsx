import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FILTER_CATEGORIES } from './constants'

interface TaskFiltersProps {
  selectedCategory: string
  onCategoryChange: (category: string) => void
  categoryCounts: Record<string, number>
}

export function TaskFilters({
  selectedCategory,
  onCategoryChange,
  categoryCounts,
}: TaskFiltersProps) {
  return (
    <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
        定时任务列表
      </h2>
      <Select value={selectedCategory} onValueChange={onCategoryChange}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder="选择分类" />
        </SelectTrigger>
        <SelectContent>
          {FILTER_CATEGORIES.map(cat => (
            <SelectItem key={cat} value={cat}>
              {`${cat}（${categoryCounts[cat] ?? 0}）`}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
