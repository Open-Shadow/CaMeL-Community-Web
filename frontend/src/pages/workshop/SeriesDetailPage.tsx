import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import ArticleCard from '@/components/workshop/ArticleCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { getSeries, type SeriesDetail } from '@/lib/workshop'

export default function SeriesDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [series, setSeries] = useState<SeriesDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    let active = true

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const data = await getSeries(Number(id))
        if (active) setSeries(data)
      } catch (err: any) {
        if (active) setError(err.response?.data?.detail || '系列详情加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [id])

  if (loading) {
    return <div className="mx-auto max-w-5xl px-4 py-8 text-sm text-muted-foreground">加载系列详情...</div>
  }

  if (error || !series) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <EmptyState
          title="系列不可用"
          description={error || '未找到对应系列'}
          action={
            <Button variant="outline" onClick={() => navigate('/workshop')}>
              返回工坊
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <section className="rounded-[28px] border bg-gradient-to-br from-orange-50 via-white to-sky-50 p-8 shadow-sm">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={series.is_completed ? 'default' : 'outline'}>
              {series.is_completed ? '系列已完成' : '系列进行中'}
            </Badge>
            {series.completion_rewarded ? <Badge className="bg-emerald-100 text-emerald-700">奖励已发放</Badge> : null}
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">{series.title}</h1>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
              {series.description || '这个系列暂时还没有补充介绍。'}
            </p>
          </div>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            <span>作者：{series.author.display_name}</span>
            <span>已发布 {series.published_count} / {series.article_count} 篇</span>
          </div>
        </div>
      </section>

      <section className="mt-8 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">系列目录</h2>
          <Button variant="outline" onClick={() => navigate('/workshop')}>
            返回文章列表
          </Button>
        </div>

        {series.articles.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">当前没有可见文章。</CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {series.articles.map((article) => (
              <ArticleCard key={article.id} article={article} onClick={() => navigate(`/workshop/${article.id}`)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
