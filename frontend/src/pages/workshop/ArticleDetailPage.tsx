import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Eye, Link2, Sparkles } from 'lucide-react'

import { EmptyState } from '@/components/shared/empty-state'
import { DetailSkeleton } from '@/components/shared/loading-skeleton'
import { CommentSection } from '@/components/workshop/CommentSection'
import ArticleCard from '@/components/workshop/ArticleCard'
import { ArticleRenderer } from '@/components/workshop/ArticleRenderer'
import { VoteButtons } from '@/components/workshop/VoteButtons'
import { TipDialog } from '@/components/workshop/tip-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuth } from '@/hooks/use-auth'
import {
  addArticleComment,
  getArticle,
  listRelatedArticles,
  listArticleComments,
  pinArticleComment,
  publishArticle,
  removeArticleCommentVote,
  removeArticleVote,
  voteArticleComment,
  voteArticle,
  type ArticleComment,
  type ArticleDetail,
  type RecommendedArticle,
} from '@/lib/workshop'
import { formatCurrency, formatDate } from '@/lib/utils'

const DIFFICULTY_LABELS: Record<ArticleDetail['difficulty'], string> = {
  BEGINNER: '入门',
  INTERMEDIATE: '进阶',
  ADVANCED: '高级',
}

const TYPE_LABELS: Record<ArticleDetail['article_type'], string> = {
  TUTORIAL: '教程',
  CASE_STUDY: '案例',
  PITFALL: '踩坑记录',
  REVIEW: '评测',
  DISCUSSION: '讨论',
}

export default function ArticleDetailPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { isAuthenticated, user } = useAuth()

  const [article, setArticle] = useState<ArticleDetail | null>(null)
  const [comments, setComments] = useState<ArticleComment[]>([])
  const [relatedArticles, setRelatedArticles] = useState<RecommendedArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [commentSubmitting, setCommentSubmitting] = useState(false)
  const [voteSubmitting, setVoteSubmitting] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [tipOpen, setTipOpen] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    let active = true

    const fetchDetail = async () => {
      setLoading(true)
      setError('')
      try {
        const [articleData, commentData] = await Promise.all([
          getArticle(Number(id)),
          listArticleComments(Number(id)).catch(() => []),
        ])
        const relatedData = await listRelatedArticles(Number(id), 4).catch(() => [])
        if (!active) return
        setArticle(articleData)
        setComments(commentData)
        setRelatedArticles(relatedData)
      } catch (err: any) {
        if (!active) return
        setError(err.response?.data?.detail || '文章详情加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchDetail()

    return () => {
      active = false
    }
  }, [id])

  const refreshComments = async () => {
    if (!id) return
    const data = await listArticleComments(Number(id))
    setComments(data)
  }

  const handleTipSuccess = (amount: number) => {
    if (article) setArticle({ ...article, total_tips: article.total_tips + amount })
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <DetailSkeleton />
      </div>
    )
  }

  if (error || !article) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <EmptyState
          title="文章详情不可用"
          description={error || '未找到对应文章'}
          action={
            <Button variant="outline" onClick={() => navigate('/workshop')}>
              返回工坊
            </Button>
          }
        />
      </div>
    )
  }

  const canManage = user?.id === article.author.id
  const canTip = isAuthenticated && user?.id !== article.author.id

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" onClick={() => navigate('/workshop')}>
          ← 返回工坊
        </Button>
        {canManage && article.status === 'DRAFT' ? (
          <Button
            disabled={publishing}
            onClick={async () => {
              setPublishing(true)
              try {
                const published = await publishArticle(article.id)
                setArticle(published)
              } catch (err: any) {
                setError(err.response?.data?.detail || '发布失败')
              } finally {
                setPublishing(false)
              }
            }}
          >
            {publishing ? '发布中...' : '发布文章'}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_0.7fr]">
        <div className="space-y-6">
          <section className="rounded-[28px] border bg-white p-6 shadow-sm">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge variant="secondary">{DIFFICULTY_LABELS[article.difficulty]}</Badge>
              <Badge variant="outline">{TYPE_LABELS[article.article_type]}</Badge>
              {article.is_featured ? (
                <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">
                  <Sparkles className="mr-1 h-3 w-3" />
                  精选
                </Badge>
              ) : null}
              {article.status !== 'PUBLISHED' ? (
                <Badge variant="outline">{article.status}</Badge>
              ) : null}
            </div>

            <h1 className="mb-4 text-4xl font-bold tracking-tight text-slate-900">{article.title}</h1>

            <div className="mb-4 flex flex-wrap gap-2">
              {article.model_tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
              {article.custom_tags.map((tag) => (
                <Badge key={tag} variant="secondary">
                  #{tag}
                </Badge>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span>{article.author.display_name}</span>
              <span>{article.author.level}</span>
              <span>{formatDate(article.published_at || article.created_at)}</span>
              <span className="inline-flex items-center gap-1">
                <Eye className="h-4 w-4" />
                {article.view_count}
              </span>
            </div>

            {article.is_outdated ? (
              <div className="mt-5 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                此文章涉及的模型版本可能已更新，请结合当前官方文档复核。
              </div>
            ) : null}

            {error ? <div className="mt-5 text-sm text-rose-600">{error}</div> : null}
          </section>

          <section className="rounded-[28px] border bg-white p-6 shadow-sm">
            <ArticleRenderer content={article.content} />
          </section>

          <section className="space-y-4">
            <VoteButtons
              netVotes={article.net_votes}
              myVote={article.my_vote}
              disabled={voteSubmitting || !isAuthenticated}
              onVote={async (value) => {
                if (!id) return
                setVoteSubmitting(true)
                try {
                  const result = await voteArticle(Number(id), value)
                  setArticle((current) =>
                    current ? { ...current, net_votes: result.net_votes, my_vote: result.my_vote } : current,
                  )
                } finally {
                  setVoteSubmitting(false)
                }
              }}
              onRemove={async () => {
                if (!id) return
                setVoteSubmitting(true)
                try {
                  const result = await removeArticleVote(Number(id))
                  setArticle((current) =>
                    current ? { ...current, net_votes: result.net_votes, my_vote: null } : current,
                  )
                } finally {
                  setVoteSubmitting(false)
                }
              }}
            />
            {canTip && (
              <Button onClick={() => setTipOpen(true)} variant="outline">
                打赏作者
              </Button>
            )}
            {!isAuthenticated ? (
              <div className="text-sm text-muted-foreground">登录后可参与投票与评论。</div>
            ) : null}
          </section>

          <CommentSection
            comments={comments}
            canPin={canManage}
            isAuthenticated={isAuthenticated}
            submitting={commentSubmitting}
            onSubmit={async (content, parentId) => {
              if (!id) return
              setCommentSubmitting(true)
              try {
                await addArticleComment(Number(id), content, parentId)
                await refreshComments()
                setArticle((current) =>
                  current ? { ...current, comment_count: current.comment_count + 1 } : current,
                )
              } finally {
                setCommentSubmitting(false)
              }
            }}
            onPin={async (commentId) => {
              if (!id) return
              setCommentSubmitting(true)
              try {
                await pinArticleComment(Number(id), commentId)
                await refreshComments()
              } finally {
                setCommentSubmitting(false)
              }
            }}
            onVote={async (commentId, value) => {
              await voteArticleComment(commentId, value)
              await refreshComments()
            }}
            onRemoveVote={async (commentId) => {
              await removeArticleCommentVote(commentId)
              await refreshComments()
            }}
          />

          {relatedArticles.length > 0 ? (
            <section className="space-y-4">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">相关文章</h2>
                <p className="text-sm text-muted-foreground">根据模型标签、关联 Skill 和内容主题推荐。</p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {relatedArticles.map((item) => (
                  <div key={item.id} className="space-y-2">
                    <ArticleCard article={item} onClick={() => navigate(`/workshop/${item.id}`)} />
                    <p className="px-1 text-xs text-muted-foreground">{item.recommendation_reason}</p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="space-y-5">
          {article.related_skill ? (
            <Card>
              <CardContent className="space-y-3 p-5">
                <div className="text-sm font-medium text-slate-500">关联 Skill</div>
                <div className="text-lg font-semibold text-slate-900">{article.related_skill.name}</div>
                <div className="text-sm text-muted-foreground">
                  {article.related_skill.creator_name} · {article.related_skill.avg_rating.toFixed(1)} 分
                </div>
                <div className="text-sm text-slate-600">
                  {article.related_skill.pricing_model === 'FREE'
                    ? '免费'
                    : `${formatCurrency(article.related_skill.price)}`}
                </div>
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={() => navigate(`/marketplace/${article.related_skill?.id}`)}
                >
                  <Link2 className="mr-2 h-4 w-4" />
                  去使用 Skill
                </Button>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardContent className="space-y-3 p-5">
              <div className="text-sm font-medium text-slate-500">互动概览</div>
              <div className="flex items-center justify-between text-sm">
                <span>净票</span>
                <span>{article.net_votes.toFixed(1)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>评论</span>
                <span>{article.comment_count}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>累计打赏</span>
                <span>{formatCurrency(article.total_tips)}</span>
              </div>
              {canTip ? (
                <Button type="button" className="w-full" variant="outline" onClick={() => setTipOpen(true)}>
                  打赏作者
                </Button>
              ) : (
                <Button type="button" className="w-full" variant="outline" disabled>
                  打赏功能需登录
                </Button>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>

      {article && (
        <TipDialog
          articleId={article.id}
          articleTitle={article.title}
          open={tipOpen}
          onClose={() => setTipOpen(false)}
          onSuccess={handleTipSuccess}
        />
      )}
    </div>
  )
}
