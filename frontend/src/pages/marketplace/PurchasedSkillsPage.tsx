import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/empty-state'
import { SkillCardSkeleton } from '@/components/shared/loading-skeleton'
import { useAuth } from '@/hooks/use-auth'
import { downloadSkill, listPurchasedSkills, type SkillPurchaseDetail } from '@/lib/skills'
import { formatCurrency, formatDate } from '@/lib/utils'

const CATEGORIES = [
  { value: '', label: '全部' },
  { value: 'CODE_DEV', label: '代码开发' },
  { value: 'WRITING', label: '文案写作' },
  { value: 'DATA_ANALYTICS', label: '数据分析' },
  { value: 'ACADEMIC', label: '学术研究' },
  { value: 'TRANSLATION', label: '翻译' },
  { value: 'CREATIVE', label: '创意设计' },
  { value: 'AGENT', label: 'Agent 工具' },
  { value: 'PRODUCTIVITY', label: '办公效率' },
  { value: 'MISC', label: '其他' },
]

export default function PurchasedSkillsPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()
  const [purchases, setPurchases] = useState<SkillPurchaseDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

  useEffect(() => {
    if (!isAuthenticated) return

    let active = true
    const fetch = async () => {
      setLoading(true)
      setError('')
      try {
        const data = await listPurchasedSkills()
        if (active) setPurchases(data)
      } catch (err: any) {
        if (active) {
          setError(err?.response?.data?.detail || '已购 Skill 列表加载失败')
          setPurchases([])
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    fetch()
    return () => { active = false }
  }, [isAuthenticated])

  if (isLoading || !isAuthenticated) {
    return <div className="py-12 text-center text-sm text-muted-foreground">加载中...</div>
  }

  const filtered = purchases.filter((p) => {
    if (category && p.category !== category) return false
    if (q && !p.name.toLowerCase().includes(q.toLowerCase()) && !p.description.toLowerCase().includes(q.toLowerCase())) return false
    return true
  })

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">已购 Skill</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          管理你购买过的 Skill，直接下载使用。
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-3">
        <Input
          placeholder="搜索已购 Skill..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-56"
        />
        {CATEGORIES.map((c) => (
          <Button
            key={c.value}
            variant={category === c.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategory(c.value)}
          >
            {c.label}
          </Button>
        ))}
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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkillCardSkeleton key={i} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="没有找到已购 Skill"
          description={purchases.length === 0 ? '你还没有购买任何 Skill。' : '当前筛选条件下没有匹配的 Skill。'}
          action={
            <Button onClick={() => navigate('/marketplace')}>
              去市场看看
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <Card key={p.purchase_id} className="transition-shadow hover:shadow-md">
              <CardContent className="space-y-3 p-5">
                <div className="flex items-center justify-between gap-3">
                  <Badge variant="secondary">{p.category}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {formatCurrency(p.paid_amount)}
                  </span>
                </div>
                <div>
                  <h3
                    className="line-clamp-1 cursor-pointer text-lg font-semibold hover:underline"
                    onClick={() => navigate(`/marketplace/${p.id}`)}
                  >
                    {p.name}
                  </h3>
                  <p className="line-clamp-2 text-sm text-muted-foreground">{p.description}</p>
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>by {p.creator_name}</span>
                  <span>⭐ {p.avg_rating.toFixed(1)}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  购买于 {formatDate(p.purchased_at)}
                </div>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => downloadSkill(p.id)}
                >
                  <Download className="mr-2 h-4 w-4" /> 下载
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
