import { useDeferredValue, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, PenLine, Search } from 'lucide-react'

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
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">知识工坊</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">沉淀 AI 实战方法、排错记录和可复用工作流</p>
        </div>
        <Button onClick={() => navigate('/workshop/create')}>
          <PenLine className="mr-1.5 h-4 w-4" />
          写文章
        </Button>
      </div>

      <div className="mb-6 space-y-3 rounded-xl border bg-card p-4">
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr_1fr]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索文章、标签或问题场景..."
              value={q}
              onChange={(event) => setQ(event.target.value)}
              className="pl-9"
            />
          </div>
          <select
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
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
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
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

        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
            value={sort}
            onChange={(event) => setSort(event.target.value as (typeof SORT_OPTIONS)[number]['value'])}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                按{option.label}排序
              </option>
            ))}
          </select>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => setModelTag('')}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                modelTag === ''
                  ? 'bg-primary text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'
              }`}
            >
              全部模型
            </button>
            {MODEL_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => setModelTag(tag)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  modelTag === tag
                    ? 'bg-primary text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {myDrafts.length > 0 ? (
        <section className="mb-8 space-y-3 rounded-xl border border-amber-200/50 bg-amber-50/30 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold">我的草稿</h2>
              <Badge variant="secondary" className="text-xs">{myDrafts.length}</Badge>
            </div>
            <span className="text-xs text-muted-foreground">点击继续编辑或发布</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {myDrafts.map((article) => (
              <ArticleCard
                key={article.id}
                article={article}
                onClick={() => navigate(`/workshop/${article.id}/edit`)}
              />
            ))}
          </div>
        </section>
      ) : null}

      {featuredArticles.length > 0 && !deferredQuery ? (
        <section className="mb-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">本周精选</h2>
            <span className="text-xs text-muted-foreground">高质量沉淀内容</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
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

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            {deferredQuery ? '搜索结果' : '最新文章'}
          </h2>
          <span className="text-xs text-muted-foreground">{articles.length} 篇</span>
        </div>

        {error ? (
          <EmptyState
            title="加载失败"
            description={error}
            action={
              <Button variant="outline" onClick={() => window.location.reload()}>
                重新加载
              </Button>
            }
          />
        ) : loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <ArticleCardSkeleton key={index} />
            ))}
          </div>
        ) : articles.length === 0 ? (
          <EmptyState
            title="暂无匹配文章"
            description="调整筛选条件，或发布第一篇解决方案文章。"
            action={<Button onClick={() => navigate('/workshop/create')}>写第一篇文章</Button>}
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
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
