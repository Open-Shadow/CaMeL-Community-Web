import { Badge } from '@/components/ui/badge'
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
      className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="space-y-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <Badge variant="secondary" className="text-xs">
            {CATEGORY_LABELS[skill.category] || skill.category}
          </Badge>
          <span className="text-sm font-semibold text-primary">
            {skill.pricing_model === 'FREE'
              ? '免费'
              : `${formatCurrency(skill.price)}`}
          </span>
        </div>

        <div className="space-y-1.5">
          <h3 className="line-clamp-1 text-base font-semibold group-hover:text-primary">{skill.name}</h3>
          <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
            {skill.description}
          </p>
        </div>

        {skill.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {skill.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
          <span>{skill.creator_name}</span>
          <span>
            {skill.avg_rating.toFixed(1)} · {skill.total_calls} 次调用
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
