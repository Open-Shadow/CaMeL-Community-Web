import { startTransition, useEffect, useState } from 'react'
import { ArrowRight, Compass, Layers3, Sparkles } from 'lucide-react'
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
    system_prompt: '',
    user_prompt_template: '',
    output_format: 'text',
    example_input: '',
    example_output: '',
    status: 'APPROVED',
    is_featured: false,
    current_version: 1,
    rejection_reason: '',
    creator_id: 0,
    created_at: '',
    updated_at: '',
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
    <div className="mx-auto max-w-6xl px-4 py-8">
      <section className="relative overflow-hidden rounded-[32px] border bg-[radial-gradient(circle_at_top_left,_#fef3c7,_transparent_32%),radial-gradient(circle_at_bottom_right,_#bfdbfe,_transparent_28%),linear-gradient(135deg,_#fffdf7,_#f8fafc)] p-8 shadow-sm">
        <div className="max-w-3xl space-y-5">
          <Badge className="bg-slate-900 text-white hover:bg-slate-900">Personalized Home</Badge>
          <div className="space-y-3">
            <h1 className="text-4xl font-bold tracking-tight text-slate-900">
              {isAuthenticated && user ? `继续推进 ${user.display_name || user.username} 的创作与交易流` : '把 Skill、文章和系列沉淀串成一条工作流'}
            </h1>
            <p className="max-w-2xl text-sm leading-7 text-slate-600">
              首页现在会结合你的调用历史与阅读轨迹给出推荐；未登录时则回退到社区热门 Skill、精选文章和系列目录。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => navigate('/marketplace')}>
              进入技能市场
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
            <Button variant="outline" onClick={() => navigate('/workshop')}>
              浏览知识工坊
            </Button>
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-8 xl:grid-cols-[1.3fr_0.7fr]">
        <div className="space-y-8">
          <SectionTitle
            icon={<Sparkles className="h-4 w-4" />}
            title={isAuthenticated ? '推荐 Skill' : '热门 Skill'}
            description={isAuthenticated ? '基于你的近期调用偏好生成' : '按精选、调用量和评分综合排序'}
          />
          {loading ? (
            <div className="text-sm text-muted-foreground">加载首页推荐...</div>
          ) : (isAuthenticated ? recommendedSkills : []).length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {recommendedSkills.map((skill) => (
                <div key={skill.id} className="space-y-2">
                  <SkillCard skill={normalizeRecommendedSkill(skill)} onClick={() => navigate(`/marketplace/${skill.id}`)} />
                  <p className="px-1 text-xs text-muted-foreground">{skill.recommendation_reason}</p>
                </div>
              ))}
            </div>
          ) : trendingSkills.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {trendingSkills.map((skill) => (
                <SkillCard key={skill.id} skill={skill} onClick={() => navigate(`/marketplace/${skill.id}`)} />
              ))}
            </div>
          ) : (
            <EmptyState title="暂时没有推荐 Skill" description="稍后再来看看社区最新上架内容。" />
          )}

          <SectionTitle
            icon={<Compass className="h-4 w-4" />}
            title={isAuthenticated ? '推荐文章' : '精选文章'}
            description={isAuthenticated ? '结合阅读轨迹、模型标签和相关 Skill 主题' : '从当前工坊内容里挑选的高质量沉淀'}
          />
          {(isAuthenticated ? recommendedArticles : featuredArticles).length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {(isAuthenticated ? recommendedArticles : featuredArticles).map((article) => (
                <div key={article.id} className="space-y-2">
                  <ArticleCard article={article} featured={article.is_featured} onClick={() => navigate(`/workshop/${article.id}`)} />
                  <p className="px-1 text-xs text-muted-foreground">{article.recommendation_reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂时没有推荐文章" description="当你开始阅读或投票后，这里会逐渐个性化。" />
          )}
        </div>

        <aside className="space-y-6">
          <SectionTitle
            icon={<Layers3 className="h-4 w-4" />}
            title="系列目录"
            description="追踪一条主题的连续产出与完成奖励"
          />
          <div className="space-y-4">
            {seriesList.length === 0 ? (
              <Card>
                <CardContent className="p-5 text-sm text-muted-foreground">当前还没有公开系列。</CardContent>
              </Card>
            ) : (
              seriesList.map((series) => (
                <Card key={series.id} className="cursor-pointer transition hover:shadow-md" onClick={() => navigate(`/workshop/series/${series.id}`)}>
                  <CardHeader className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-lg">{series.title}</CardTitle>
                      <Badge variant={series.is_completed ? 'default' : 'outline'}>
                        {series.is_completed ? '已完成' : '进行中'}
                      </Badge>
                    </div>
                    <p className="line-clamp-3 text-sm text-muted-foreground">{series.description || '这个系列还没有填写简介。'}</p>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm text-muted-foreground">
                    <div className="flex items-center justify-between">
                      <span>{series.author.display_name}</span>
                      <span>{series.published_count}/{series.article_count} 篇</span>
                    </div>
                    {series.completion_rewarded ? (
                      <div className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-700">已发放系列完成奖励</div>
                    ) : null}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
          <Button asChild variant="outline" className="w-full">
            <Link to="/workshop">查看全部文章与系列</Link>
          </Button>
        </aside>
      </div>
    </div>
  )
}

function SectionTitle({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        {icon}
        <span>{title}</span>
      </div>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  )
}
