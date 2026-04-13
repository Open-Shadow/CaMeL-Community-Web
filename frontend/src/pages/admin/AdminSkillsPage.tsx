import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { api, useAuth } from '@/hooks/use-auth'
import { formatDateTime } from '@/lib/utils'

interface SkillReviewQueueItem {
  id: number
  name: string
  description: string
  category: string
  tags: string[]
  pricing_model: string
  price: number | null
  status: string
  rejection_reason: string
  creator_id: number
  creator_name: string
  created_at: string
  updated_at: string
  is_featured?: boolean
  pending_version: string | null
  pending_version_id: number | null
  pending_version_changelog: string | null
}

interface SkillReviewQueueResponse {
  items: SkillReviewQueueItem[]
  total: number
  page: number
  page_size: number
}

const STATUS_OPTIONS = [
  { value: 'pending', label: '待审核' },
  { value: 'rejected', label: '已拒绝' },
  { value: 'approved', label: '已上架' },
  { value: 'all', label: '全部' },
]

export default function AdminSkillsPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<SkillReviewQueueItem[]>([])
  const [status, setStatus] = useState('pending')
  const [q, setQ] = useState('')
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [rejectReasons, setRejectReasons] = useState<Record<number, string>>({})
  const [actioningId, setActioningId] = useState<number | null>(null)

  const canFeature = useMemo(() => user?.role === 'ADMIN' || user?.role === 'MODERATOR', [user?.role])

  const loadQueue = async () => {
    setIsLoading(true)
    setMessage('')
    try {
      const response = await api.get<SkillReviewQueueResponse>('/admin/skills/review-queue', {
        params: {
          status,
          q: q.trim() || undefined,
          page: 1,
          page_size: 50,
        },
      })
      setItems(response.data.items)
      setTotal(response.data.total)
    } catch (err: any) {
      setMessage(err.response?.data?.message || '审核队列加载失败')
      setItems([])
      setTotal(0)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadQueue()
  }, [status])

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault()
    await loadQueue()
  }

  const handleReview = async (item: SkillReviewQueueItem, action: 'APPROVE' | 'REJECT') => {
    setActioningId(item.id)
    setMessage('')
    try {
      const reason = rejectReasons[item.id] || ''
      const response = await api.post<SkillReviewQueueItem>(`/admin/skills/${item.id}/review`, {
        action,
        reason,
        ...(item.pending_version_id != null ? { version_id: item.pending_version_id } : {}),
      })
      setItems((current) => current.map((skill) => (skill.id === item.id ? response.data : skill)))
      await loadQueue()
    } catch (err: any) {
      setMessage(err.response?.data?.message || '审核操作失败')
    } finally {
      setActioningId(null)
    }
  }

  const handleFeatureToggle = async (item: SkillReviewQueueItem, nextFeatured: boolean) => {
    setActioningId(item.id)
    setMessage('')
    try {
      const response = await api.post<SkillReviewQueueItem>(`/admin/skills/${item.id}/featured`, {
        is_featured: nextFeatured,
      })
      setItems((current) => current.map((skill) => (skill.id === item.id ? response.data : skill)))
    } catch (err: any) {
      setMessage(err.response?.data?.message || '更新精选状态失败')
    } finally {
      setActioningId(null)
    }
  }

  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Skill 审核</h1>
        <p className="text-muted-foreground">自动检测通过后，人工审核决定是否上架。</p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4">
          <form onSubmit={handleSearch} className="flex flex-wrap gap-3">
            <Input
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="搜索 Skill 名称、简介、创作者"
              className="max-w-md"
            />
            <Button type="submit" variant="outline">搜索</Button>
          </form>

          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((option) => (
              <Button
                key={option.value}
                variant={status === option.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatus(option.value)}
              >
                {option.label}
              </Button>
            ))}
            <Badge variant="secondary">共 {total} 条</Badge>
          </div>
        </CardContent>
      </Card>

      {message ? (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{message}</div>
      ) : null}

      {isLoading ? (
        <div className="py-8 text-sm text-muted-foreground">加载审核队列中...</div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            当前筛选条件下没有 Skill。
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <Card key={item.id}>
              <CardHeader className="space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <CardTitle className="text-lg">{item.name}</CardTitle>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={item.status === 'SCANNING' ? 'default' : 'outline'}>{item.status}</Badge>
                    {item.is_featured ? <Badge>精选</Badge> : null}
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  by {item.creator_name} · {item.category} · {item.pricing_model === 'FREE' ? '免费' : `$${(item.price ?? 0).toFixed(2)}`}
                </div>
                <div className="text-xs text-muted-foreground">
                  创建 {formatDateTime(item.created_at)} · 更新 {formatDateTime(item.updated_at)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{item.description}</p>
                {item.tags.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {item.tags.map((tag) => (
                      <Badge key={`${item.id}-${tag}`} variant="secondary">#{tag}</Badge>
                    ))}
                  </div>
                ) : null}

                {item.rejection_reason ? (
                  <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    拒绝原因：{item.rejection_reason}
                  </div>
                ) : null}

                <div className="space-y-2">
                  <label className="text-sm font-medium">审核备注（拒绝时必填）</label>
                  <Textarea
                    rows={3}
                    value={rejectReasons[item.id] || ''}
                    onChange={(event) =>
                      setRejectReasons((current) => ({ ...current, [item.id]: event.target.value }))
                    }
                    placeholder="请输入拒绝原因或审核备注"
                  />
                </div>

                {item.pending_version_id != null ? (
                  <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
                    待审核新版本：v{item.pending_version}
                    {item.pending_version_changelog ? ` — ${item.pending_version_changelog}` : ''}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <Button
                    disabled={actioningId === item.id || (item.status !== 'SCANNING' && item.pending_version_id == null)}
                    onClick={() => void handleReview(item, 'APPROVE')}
                  >
                    审核通过
                  </Button>
                  <Button
                    variant="destructive"
                    disabled={actioningId === item.id || (item.status !== 'SCANNING' && item.pending_version_id == null)}
                    onClick={() => void handleReview(item, 'REJECT')}
                  >
                    审核拒绝
                  </Button>
                  {canFeature ? (
                    <Button
                      variant="outline"
                      disabled={actioningId === item.id || item.status !== 'APPROVED'}
                      onClick={() => void handleFeatureToggle(item, !item.is_featured)}
                    >
                      {item.is_featured ? '取消精选' : '设为精选'}
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
