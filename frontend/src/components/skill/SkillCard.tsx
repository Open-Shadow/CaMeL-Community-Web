import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { SkillSummary } from '@/lib/skills'
import { formatCurrency } from '@/lib/utils'

interface SkillCardProps {
  skill: SkillSummary
  onClick?: () => void
}

const CATEGORY_LABELS: Record<string, string> = {
  CODE_DEV: '代码开发',
  WRITING: '文案写作',
  DATA_ANALYTICS: '数据分析',
  ACADEMIC: '学术研究',
  TRANSLATION: '翻译本地化',
  CREATIVE: '创意设计',
  AGENT: 'Agent 工具',
  PRODUCTIVITY: '办公效率',
  MISC: '其他',
}

export default function SkillCard({ skill, onClick }: SkillCardProps) {
  return (
    <Card
      className="cursor-pointer border-border/70 transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="secondary">
            {CATEGORY_LABELS[skill.category] || skill.category}
          </Badge>
          <span className="text-sm font-semibold text-amber-600">
            {skill.pricing_model === 'FREE'
              ? '免费'
              : `${formatCurrency(skill.price_per_use)}/次`}
          </span>
        </div>

        <div className="space-y-2">
          <h3 className="line-clamp-1 text-lg font-semibold">{skill.name}</h3>
          <p className="line-clamp-3 text-sm text-muted-foreground">
            {skill.description}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {skill.tags.slice(0, 4).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              #{tag}
            </Badge>
          ))}
        </div>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>by {skill.creator_name}</span>
          <span>
            ⭐ {skill.avg_rating.toFixed(1)} · {skill.total_calls} 次调用
          </span>
        </div>

        <Button className="w-full" variant="outline">
          查看详情
        </Button>
      </CardContent>
    </Card>
  )
}
