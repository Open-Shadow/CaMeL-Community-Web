import { useDeferredValue, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { ArticleCardSkeleton } from '@/components/shared/loading-skeleton'
import ArticleCard from '@/components/workshop/ArticleCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/use-auth'
import {
  listArticles,
  listFeaturedArticles,
  listMyArticles,
  searchArticles,
  type ArticleSummary,
} from '@/lib/workshop'

const DIFFICULTIES = [
  { value: '', label: '全部难度' },
  { value: 'BEGINNER', label: '入门' },
  { value: 'INTERMEDIATE', label: '进阶' },
  { value: 'ADVANCED', label: '高级' },
]

const ARTICLE_TYPES = [
  { value: '', label: '全部类型' },
  { value: 'TUTORIAL', label: '教程' },
  { value: 'CASE_STUDY', label: '案例' },
  { value: 'PITFALL', label: '踩坑' },
  { value: 'REVIEW', label: '评测' },
  { value: 'DISCUSSION', label: '讨论' },
]

const SORT_OPTIONS = [
  { value: 'latest', label: '最新' },
  { value: 'hot', label: '最热' },
  { value: 'featured', label: '精选优先' },
] as const

const MODEL_TAGS = ['Claude Code', 'Claude Sonnet 4', 'Claude Opus 4', 'GPT-5', '通用']

export default function WorkshopPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [q, setQ] = useState('')
  const [difficulty, setDifficulty] = useState<ArticleSummary['difficulty'] | ''>('')
  const [articleType, setArticleType] = useState<ArticleSummary['article_type'] | ''>('')
  const [modelTag, setModelTag] = useState('')
  const [sort, setSort] = useState<(typeof SORT_OPTIONS)[number]['value']>('latest')
  const [articles, setArticles] = useState<ArticleSummary[]>([])
  const [featuredArticles, setFeaturedArticles] = useState<ArticleSummary[]>([])
  const [myDrafts, setMyDrafts] = useState<ArticleSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const deferredQuery = useDeferredValue(q)

  useEffect(() => {
    let active = true

    const fetchFeatured = async () => {
      try {
        const data = await listFeaturedArticles(4)
        if (active) setFeaturedArticles(data)
      } catch {
        if (active) setFeaturedArticles([])
      }
    }

    fetchFeatured()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      setMyDrafts([])
      return
    }
    let active = true

    const fetchDrafts = async () => {
      try {
        const data = await listMyArticles('DRAFT')
        if (active) setMyDrafts(data)
      } catch {
        if (active) setMyDrafts([])
      }
    }

    fetchDrafts()
    return () => {
      active = false
    }
  }, [isAuthenticated])

  useEffect(() => {
    let active = true

    const fetchArticles = async () => {
      setLoading(true)
      setError('')

      try {
        const data = deferredQuery
          ? (await searchArticles({
              q: deferredQuery,
              difficulty: difficulty || undefined,
              article_type: articleType || undefined,
              model_tag: modelTag || undefined,
              limit: 50,
            })).items
          : await listArticles({
              difficulty: difficulty || undefined,
              article_type: articleType || undefined,
              model_tag: modelTag || undefined,
              sort,
            })

        if (active) setArticles(data)
      } catch (err: any) {
        if (active) {
          setArticles([])
          setError(err.response?.data?.detail || '文章列表加载失败')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchArticles()

    return () => {
      active = false
    }
  }, [articleType, deferredQuery, difficulty, modelTag, sort])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <section className="mb-8 rounded-[28px] bg-gradient-to-br from-amber-50 via-white to-sky-50 p-6 shadow-sm ring-1 ring-slate-200">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
              Workshop
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">知识工坊</h1>
            <p className="text-sm leading-6 text-slate-600">
              沉淀 AI 实战方法、排错记录和可复用工作流。先把问题、方案、效果写清楚，再让 Skill 与文章形成闭环。
            </p>
          </div>
          <Button className="h-11 px-5" onClick={() => navigate('/workshop/create')}>
            写文章
          </Button>
        </div>
      </section>

      <section className="mb-8 space-y-4 rounded-3xl border bg-white p-5">
        <div className="grid gap-3 lg:grid-cols-[2fr_1fr_1fr]">
          <Input
            placeholder="搜索文章、标签或问题场景..."
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />
          <select
            className="rounded-md border bg-background px-3 py-2 text-sm"
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as ArticleSummary['difficulty'] | '')}
          >
            {DIFFICULTIES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-md border bg-background px-3 py-2 text-sm"
            value={articleType}
            onChange={(event) => setArticleType(event.target.value as ArticleSummary['article_type'] | '')}
          >
            {ARTICLE_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            className="rounded-md border bg-background px-3 py-2 text-sm"
            value={sort}
            onChange={(event) => setSort(event.target.value as (typeof SORT_OPTIONS)[number]['value'])}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                按{option.label}排序
              </option>
            ))}
          </select>
          <Button
            type="button"
            size="sm"
            variant={modelTag === '' ? 'default' : 'outline'}
            onClick={() => setModelTag('')}
          >
            全部模型
          </Button>
          {MODEL_TAGS.map((tag) => (
            <Button
              key={tag}
              type="button"
              size="sm"
              variant={modelTag === tag ? 'default' : 'outline'}
              onClick={() => setModelTag(tag)}
            >
              {tag}
            </Button>
          ))}
        </div>
      </section>

      {myDrafts.length > 0 ? (
        <section className="mb-8 space-y-4 rounded-3xl border border-amber-200 bg-amber-50/50 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">我的草稿</h2>
              <Badge variant="secondary">{myDrafts.length}</Badge>
            </div>
            <span className="text-sm text-muted-foreground">点击草稿可继续编辑或发布</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {myDrafts.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                onClick={() => navigate(`/workshop/${article.id}`)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {featuredArticles.length > 0 && !deferredQuery ? (
        <section className="mb-8 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-slate-900">本周精选</h2>
            <span className="text-sm text-muted-foreground">优先展示高质量沉淀内容</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {featuredArticles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                featured
                onClick={() => navigate(`/workshop/${article.id}`)}
              />
            ))}
          </div>
        </section>
      ) : null}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-slate-900">
            {deferredQuery ? '搜索结果' : '最新文章'}
          </h2>
          <span className="text-sm text-muted-foreground">{articles.length} 篇</span>
        </div>

        {error ? (
          <EmptyState
            title="文章列表加载失败"
            description={error}
            action={
              <Button variant="outline" onClick={() => window.location.reload()}>
                重新加载
              </Button>
            }
          />
        ) : loading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <ArticleCardSkeleton key={index} />
            ))}
          </div>
        ) : articles.length === 0 ? (
          <EmptyState
            title="暂无匹配文章"
            description="可以先调整筛选条件，或者发布第一篇解决方案文章。"
            action={<Button onClick={() => navigate('/workshop/create')}>写第一篇文章</Button>}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {articles.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                onClick={() => navigate(`/workshop/${article.id}`)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
