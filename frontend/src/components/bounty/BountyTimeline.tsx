import { Badge } from '@/components/ui/badge'

const LABELS: Record<string, string> = {
  OPEN: '开放',
  IN_PROGRESS: '进行中',
  DELIVERED: '已交付',
  IN_REVIEW: '审核中',
  REVISION: '待修改',
  DISPUTED: '争议中',
  ARBITRATING: '仲裁中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

const ORDER = ['OPEN', 'IN_PROGRESS', 'DELIVERED', 'REVISION', 'DISPUTED', 'ARBITRATING', 'COMPLETED']

export function BountyTimeline({ status }: { status: string }) {
  return (
    <div className="flex flex-wrap gap-2">
      {ORDER.map((step) => (
        <Badge key={step} variant={step === status ? 'default' : 'outline'}>
          {LABELS[step] || step}
        </Badge>
      ))}
      {status === 'CANCELLED' ? <Badge variant="destructive">已取消</Badge> : null}
    </div>
  )
}
