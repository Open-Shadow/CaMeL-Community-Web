import { MessageSquare, Star, ThumbsUp } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { ArticleSummary } from '@/lib/workshop'
import { formatDate } from '@/lib/utils'

interface ArticleCardProps {
  article: ArticleSummary
  onClick?: () => void
  featured?: boolean
}

const DIFFICULTY_LABELS: Record<ArticleSummary['difficulty'], string> = {
  BEGINNER: '入门',
  INTERMEDIATE: '进阶',
  ADVANCED: '高级',
}

const DIFFICULTY_STYLES: Record<ArticleSummary['difficulty'], string> = {
  BEGINNER: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  INTERMEDIATE: 'border-amber-200 bg-amber-50 text-amber-700',
  ADVANCED: 'border-rose-200 bg-rose-50 text-rose-700',
}

const TYPE_LABELS: Record<ArticleSummary['article_type'], string> = {
  TUTORIAL: '教程',
  CASE_STUDY: '案例',
  PITFALL: '踩坑',
  REVIEW: '评测',
  DISCUSSION: '讨论',
}

export default function ArticleCard({ article, onClick, featured = false }: ArticleCardProps) {
  return (
    <Card
      className="group cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="space-y-3 p-5">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge className={DIFFICULTY_STYLES[article.difficulty]} variant="outline">
            {DIFFICULTY_LABELS[article.difficulty]}
          </Badge>
          <Badge variant="secondary" className="text-xs">{TYPE_LABELS[article.article_type]}</Badge>
          {(article.is_featured || featured) && (
            <Badge className="border-primary/20 bg-primary/10 text-primary hover:bg-primary/10">
              <Star className="mr-1 h-3 w-3" />
              精选
            </Badge>
          )}
        </div>

        <div className="space-y-1.5">
          <h3 className="line-clamp-2 text-base font-semibold leading-snug group-hover:text-primary">{article.title}</h3>
          <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">{article.excerpt}</p>
        </div>

        {(article.model_tags.length > 0 || article.custom_tags.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {article.model_tags.slice(0, 2).map((tag) => (
              <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{tag}</span>
            ))}
            {article.custom_tags.slice(0, 2).map((tag) => (
              <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">#{tag}</span>
            ))}
          </div>
        )}

        {article.related_skill && (
          <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-foreground">
            关联 Skill: {article.related_skill.name}
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span>{article.author.display_name}</span>
            <span>{formatDate(article.published_at || article.created_at)}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <ThumbsUp className="h-3 w-3" />
              {article.net_votes.toFixed(0)}
            </span>
            <span className="inline-flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              {article.comment_count}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
