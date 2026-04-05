import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { TipDialog } from '@/components/workshop/tip-dialog'
import { useAuth } from '@/hooks/use-auth'

interface Article {
  id: number
  title: string
  content: string
  author: { id: number; display_name: string; avatar_url: string }
  total_tips: number
  net_votes: number
  published_at: string
}

interface TipRecord {
  id: number
  tipper: { id: number; display_name: string; avatar_url: string }
  amount: number
  created_at: string
}

export default function ArticleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user, isAuthenticated } = useAuth()
  const [article, setArticle] = useState<Article | null>(null)
  const [tips, setTips] = useState<TipRecord[]>([])
  const [tipOpen, setTipOpen] = useState(false)

  useEffect(() => {
    if (!id) return
    axios.get(`/api/workshop/articles/${id}`).then(r => setArticle(r.data)).catch(() => {})
    axios.get(`/api/workshop/articles/${id}/tips`).then(r => setTips(r.data)).catch(() => {})
  }, [id])

  const handleTipSuccess = (amount: number) => {
    if (article) setArticle({ ...article, total_tips: article.total_tips + amount })
    axios.get(`/api/workshop/articles/${id}/tips`).then(r => setTips(r.data)).catch(() => {})
  }

  if (!article) return <div className="container mx-auto px-4 py-8">加载中...</div>

  const canTip = isAuthenticated && user?.id !== article.author.id

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <h1 className="text-3xl font-bold mb-2">{article.title}</h1>
      <div className="flex items-center gap-3 text-sm text-muted-foreground mb-6">
        <span>{article.author.display_name}</span>
        <span>{new Date(article.published_at).toLocaleDateString()}</span>
        <span>👍 {article.net_votes}</span>
        <span>💰 ${article.total_tips.toFixed(2)}</span>
      </div>

      <div className="prose max-w-none mb-8 whitespace-pre-wrap">{article.content}</div>

      {canTip && (
        <div className="flex justify-center mb-8">
          <Button onClick={() => setTipOpen(true)} variant="outline">
            💰 打赏作者
          </Button>
        </div>
      )}

      {tips.length > 0 && (
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold mb-3">打赏记录</h3>
          <div className="space-y-2">
            {tips.map(t => (
              <div key={t.id} className="flex justify-between text-sm">
                <span>{t.tipper.display_name}</span>
                <span className="text-muted-foreground">${t.amount.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

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
