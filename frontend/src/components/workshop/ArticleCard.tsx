import { ArrowUpRight, MessageSquare, Star } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
      className="cursor-pointer border-border/70 transition-all hover:-translate-y-0.5 hover:shadow-lg"
      onClick={onClick}
    >
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={DIFFICULTY_STYLES[article.difficulty]} variant="outline">
            {DIFFICULTY_LABELS[article.difficulty]}
          </Badge>
          <Badge variant="secondary">{TYPE_LABELS[article.article_type]}</Badge>
          {article.is_featured || featured ? (
            <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">
              <Star className="mr-1 h-3 w-3" />
              精选
            </Badge>
          ) : null}
        </div>

        <div className="space-y-2">
          <h3 className="line-clamp-2 text-xl font-semibold leading-7">{article.title}</h3>
          <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">{article.excerpt}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {article.model_tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
          {article.custom_tags.slice(0, 2).map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              #{tag}
            </Badge>
          ))}
        </div>

        {article.related_skill ? (
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            关联 Skill: {article.related_skill.name}
          </div>
        ) : null}

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{article.author.display_name}</span>
          <span>{formatDate(article.published_at || article.created_at)}</span>
        </div>

        <div className="flex items-center justify-between border-t pt-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>净票 {article.net_votes.toFixed(1)}</span>
            <span className="inline-flex items-center gap-1">
              <MessageSquare className="h-4 w-4" />
              {article.comment_count}
            </span>
          </div>
          <Button variant="ghost" className="gap-1 px-0 text-slate-700">
            查看详情
            <ArrowUpRight className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
