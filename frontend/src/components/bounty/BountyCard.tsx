import { Clock } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { BountySummary } from '@/lib/bounties'
import { formatCurrency, formatDate } from '@/lib/utils'

interface BountyCardProps {
  bounty: BountySummary
  onClick?: () => void
}

const STATUS_LABELS: Record<string, string> = {
  OPEN: '开放中',
  IN_PROGRESS: '进行中',
  DELIVERED: '待验收',
  IN_REVIEW: '审核中',
  REVISION: '待修改',
  COMPLETED: '已完成',
  DISPUTED: '争议中',
  ARBITRATING: '仲裁中',
  CANCELLED: '已取消',
}

const STATUS_STYLES: Record<string, string> = {
  OPEN: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  IN_PROGRESS: 'border-blue-200 bg-blue-50 text-blue-700',
  COMPLETED: 'border-gray-200 bg-gray-50 text-gray-700',
  ARBITRATING: 'border-amber-200 bg-amber-50 text-amber-700',
}

const TYPE_LABELS: Record<string, string> = {
  SKILL_CUSTOM: 'Skill 定制',
  DATA_PROCESSING: '数据处理',
  CONTENT_CREATION: '内容创作',
  BUG_FIX: '问题修复',
  GENERAL: '通用任务',
}

export default function BountyCard({ bounty, onClick }: BountyCardProps) {
  return (
    <Card className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-md" onClick={onClick}>
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="secondary" className="text-xs">{TYPE_LABELS[bounty.bounty_type] || bounty.bounty_type}</Badge>
          <span className="text-base font-semibold text-primary">{formatCurrency(bounty.reward)}</span>
        </div>

        <div className="space-y-1.5">
          <h3 className="line-clamp-1 text-base font-semibold group-hover:text-primary">{bounty.title}</h3>
          <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">{bounty.description}</p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <Badge variant="outline" className={STATUS_STYLES[bounty.status] || ''}>
            {STATUS_LABELS[bounty.status] || bounty.status}
          </Badge>
          {bounty.is_cold && <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">冷门</Badge>}
          <Badge variant="outline" className="text-xs">{bounty.application_count} 人申请</Badge>
        </div>

        <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
          <span>{bounty.creator.display_name}</span>
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(bounty.deadline)}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
