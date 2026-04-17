import { startTransition, useEffect, useState } from 'react'
import { ArrowRight, Compass, Layers3, Sparkles, TrendingUp } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import SkillCard from '@/components/skill/SkillCard'
import ArticleCard from '@/components/workshop/ArticleCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/use-auth'
import { listRecommendedSkills, listTrendingSkills, type RecommendedSkill, type SkillSummary } from '@/lib/skills'
import {
  listFeaturedArticles,
  listRecommendedArticles,
  listSeries,
  type RecommendedArticle,
  type SeriesSummary,
} from '@/lib/workshop'

function normalizeRecommendedSkill(skill: RecommendedSkill): SkillSummary {
  return {
    ...skill,
    tags: [],
    status: 'APPROVED' as const,
    is_featured: false,
    current_version: '1.0.0',
    rejection_reason: '',
    readme_html: '',
    package_size: 0,
    download_count: 0,
    creator_id: 0,
    created_at: '',
    updated_at: '',
    has_purchased: false,
  }
}

export default function HomePage() {
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()
  const [recommendedSkills, setRecommendedSkills] = useState<RecommendedSkill[]>([])
  const [recommendedArticles, setRecommendedArticles] = useState<RecommendedArticle[]>([])
  const [trendingSkills, setTrendingSkills] = useState<SkillSummary[]>([])
  const [featuredArticles, setFeaturedArticles] = useState<RecommendedArticle[]>([])
  const [seriesList, setSeriesList] = useState<SeriesSummary[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    const load = async () => {
      setLoading(true)
      try {
        const [trending, featured, series, recSkills, recArticles] = await Promise.all([
          listTrendingSkills(4),
          listFeaturedArticles(4),
          listSeries(6),
          isAuthenticated ? listRecommendedSkills(4).catch(() => []) : Promise.resolve([]),
          isAuthenticated ? listRecommendedArticles(4).catch(() => []) : Promise.resolve([]),
        ])

        if (!active) return
        startTransition(() => {
          setTrendingSkills(trending.map((item) => normalizeRecommendedSkill({ ...item, recommendation_reason: '' })))
          setFeaturedArticles(featured.map((item) => ({ ...item, recommendation_reason: '社区精选内容' })))
          setSeriesList(series)
          setRecommendedSkills(recSkills)
          setRecommendedArticles(recArticles)
        })
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [isAuthenticated])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <section className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/5 via-white to-red-50 px-8 py-12 sm:px-12 sm:py-16">
        <div className="absolute right-0 top-0 -z-10 h-64 w-64 rounded-full bg-primary/5 blur-3xl" />
        <div className="max-w-2xl space-y-5">
          <Badge className="border-primary/20 bg-primary/10 text-primary hover:bg-primary/10">
            {isAuthenticated ? 'Personalized Home' : 'AI Community Platform'}
          </Badge>
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {isAuthenticated && user
              ? `欢迎回来，${user.display_name || user.username}`
              : '探索 AI 技能、悬赏与知识'}
          </h1>
          <p className="text-sm leading-7 text-muted-foreground sm:text-base">
            {isAuthenticated
              ? '基于你的调用历史与阅读轨迹，为你推荐最相关的 Skill 和文章。'
              : '在 CaMeL Community 发现优质 Prompt/Skill，发布悬赏任务，沉淀 AI 实战经验。'}
          </p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => navigate('/marketplace')} size="lg">
              进入技能市场
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline" size="lg" onClick={() => navigate('/workshop')}>
              浏览知识工坊
            </Button>
          </div>
        </div>
      </section>

      <div className="mt-10 grid gap-10 xl:grid-cols-[1fr_320px]">
        <div className="space-y-10">
          <section className="space-y-4">
            <SectionHeader
              icon={<Sparkles className="h-4 w-4 text-primary" />}
              title={isAuthenticated ? '为你推荐' : '热门 Skill'}
              description={isAuthenticated ? '基于近期调用偏好生成' : '按调用量和评分综合排序'}
              linkTo="/marketplace"
              linkLabel="查看全部"
            />
            {loading ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-48 animate-pulse rounded-xl border bg-muted/50" />
                ))}
              </div>
            ) : (isAuthenticated ? recommendedSkills : []).length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {recommendedSkills.map((skill) => (
                  <div key={skill.id} className="space-y-1.5">
                    <SkillCard skill={normalizeRecommendedSkill(skill)} onClick={() => navigate(`/marketplace/${skill.id}`)} />
                    {skill.recommendation_reason && (
                      <p className="px-1 text-xs text-muted-foreground">{skill.recommendation_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : trendingSkills.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {trendingSkills.map((skill) => (
                  <SkillCard key={skill.id} skill={skill} onClick={() => navigate(`/marketplace/${skill.id}`)} />
                ))}
              </div>
            ) : (
              <EmptyState title="暂时没有推荐 Skill" description="稍后再来看看社区最新上架内容。" />
            )}
          </section>

          <section className="space-y-4">
            <SectionHeader
              icon={<Compass className="h-4 w-4 text-primary" />}
              title={isAuthenticated ? '推荐文章' : '精选文章'}
              description={isAuthenticated ? '结合阅读轨迹和 Skill 主题' : '高质量社区沉淀'}
              linkTo="/workshop"
              linkLabel="查看全部"
            />
            {(isAuthenticated ? recommendedArticles : featuredArticles).length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {(isAuthenticated ? recommendedArticles : featuredArticles).map((article) => (
                  <div key={article.id} className="space-y-1.5">
                    <ArticleCard article={article} featured={article.is_featured} onClick={() => navigate(`/workshop/${article.id}`)} />
                    {article.recommendation_reason && (
                      <p className="px-1 text-xs text-muted-foreground">{article.recommendation_reason}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂时没有推荐文章" description="当你开始阅读或投票后，这里会逐渐个性化。" />
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <SectionHeader
            icon={<Layers3 className="h-4 w-4 text-primary" />}
            title="系列目录"
            description="连续主题产出"
          />
          <div className="space-y-3">
            {seriesList.length === 0 ? (
              <Card>
                <CardContent className="p-5 text-sm text-muted-foreground">当前还没有公开系列。</CardContent>
              </Card>
            ) : (
              seriesList.map((series) => (
                <Card
                  key={series.id}
                  className="cursor-pointer transition-all hover:-translate-y-0.5 hover:shadow-md"
                  onClick={() => navigate(`/workshop/series/${series.id}`)}
                >
                  <CardHeader className="space-y-2 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="line-clamp-1 text-base">{series.title}</CardTitle>
                      <Badge variant={series.is_completed ? 'default' : 'outline'} className="shrink-0 text-xs">
                        {series.is_completed ? '已完成' : '进行中'}
                      </Badge>
                    </div>
                    <p className="line-clamp-2 text-sm text-muted-foreground">{series.description || '暂无简介'}</p>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between p-4 pt-0 text-xs text-muted-foreground">
                    <span>{series.author.display_name}</span>
                    <span>{series.published_count}/{series.article_count} 篇</span>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
          <Button asChild variant="outline" className="w-full">
            <Link to="/workshop">查看全部文章与系列</Link>
          </Button>

          <div className="rounded-xl border bg-gradient-to-b from-primary/5 to-transparent p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <TrendingUp className="h-4 w-4 text-primary" />
              快速入口
            </div>
            <div className="space-y-2">
              <Link to="/marketplace/create" className="block rounded-md px-3 py-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground">
                上架新 Skill
              </Link>
              <Link to="/bounty/create" className="block rounded-md px-3 py-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground">
                发布悬赏
              </Link>
              <Link to="/workshop/create" className="block rounded-md px-3 py-2 text-sm text-muted-foreground transition hover:bg-muted hover:text-foreground">
                写文章
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SectionHeader({
  icon,
  title,
  description,
  linkTo,
  linkLabel,
}: {
  icon: React.ReactNode
  title: string
  description: string
  linkTo?: string
  linkLabel?: string
}) {
  return (
    <div className="flex items-end justify-between gap-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {icon}
          <span>{title}</span>
        </div>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {linkTo && linkLabel && (
        <Link to={linkTo} className="shrink-0 text-sm font-medium text-primary hover:underline">
          {linkLabel}
        </Link>
      )}
    </div>
  )
}
