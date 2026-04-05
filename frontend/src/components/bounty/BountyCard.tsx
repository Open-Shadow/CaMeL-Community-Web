import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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

const TYPE_LABELS: Record<string, string> = {
  SKILL_CUSTOM: 'Skill 定制',
  DATA_PROCESSING: '数据处理',
  CONTENT_CREATION: '内容创作',
  BUG_FIX: '问题修复',
  GENERAL: '通用任务',
}

export default function BountyCard({ bounty, onClick }: BountyCardProps) {
  return (
    <Card className="cursor-pointer border-border/70 transition-shadow hover:shadow-md" onClick={onClick}>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="secondary">{TYPE_LABELS[bounty.bounty_type] || bounty.bounty_type}</Badge>
          <span className="text-lg font-semibold text-emerald-600">{formatCurrency(bounty.reward)}</span>
        </div>

        <div className="space-y-2">
          <h3 className="line-clamp-1 text-lg font-semibold">{bounty.title}</h3>
          <p className="line-clamp-3 text-sm text-muted-foreground">{bounty.description}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">{STATUS_LABELS[bounty.status] || bounty.status}</Badge>
          {bounty.is_cold ? <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">冷门</Badge> : null}
          <Badge variant="outline">{bounty.application_count} 人申请</Badge>
        </div>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{bounty.creator.display_name}</span>
          <span>截止 {formatDate(bounty.deadline)}</span>
        </div>

        <Button className="w-full" variant="outline">
          查看详情
        </Button>
      </CardContent>
    </Card>
  )
}
