import { useDeferredValue, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Plus, Search, Target } from 'lucide-react'

import BountyCard from '@/components/bounty/BountyCard'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { listBounties, listMyBounties, type BountySummary } from '@/lib/bounties'
import { useAuth } from '@/hooks/use-auth'

const TYPE_OPTIONS = [
  { value: '', label: '全部类型' },
  { value: 'SKILL_CUSTOM', label: 'Skill 定制' },
  { value: 'DATA_PROCESSING', label: '数据处理' },
  { value: 'CONTENT_CREATION', label: '内容创作' },
  { value: 'BUG_FIX', label: '问题修复' },
  { value: 'GENERAL', label: '通用任务' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'OPEN', label: '开放中' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'DELIVERED', label: '待验收' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'ARBITRATING', label: '仲裁中' },
]

export default function BountyListPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated } = useAuth()
  const [q, setQ] = useState('')
  const [bountyType, setBountyType] = useState('')
  const [status, setStatus] = useState('')
  const [items, setItems] = useState<BountySummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [role, setRole] = useState<'all' | 'creator' | 'hunter'>(location.pathname === '/bounty/mine' ? 'all' : 'all')

  const deferredQuery = useDeferredValue(q)

  useEffect(() => {
    let active = true

    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const response = location.pathname === '/bounty/mine' && isAuthenticated
          ? await listMyBounties(role)
          : await listBounties({
              q: deferredQuery || undefined,
              bounty_type: bountyType || undefined,
              status: status || undefined,
            })
        if (active) setItems(response.items)
      } catch (loadError: any) {
        if (active) {
          setError(loadError.response?.data?.message || '悬赏列表加载失败')
          setItems([])
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [bountyType, deferredQuery, isAuthenticated, location.pathname, role, status])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">悬赏任务板</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">发布需求、接单交付、验收仲裁</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link to="/bounty/mine">我的悬赏</Link>
          </Button>
          <Button onClick={() => navigate('/bounty/create')}>
            <Plus className="mr-1.5 h-4 w-4" />
            发布悬赏
          </Button>
        </div>
      </div>

      <div className="mb-6 space-y-3 rounded-xl border bg-card p-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索悬赏标题或描述..."
              value={q}
              onChange={(event) => setQ(event.target.value)}
              className="pl-9"
            />
          </div>
          <select
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
            value={bountyType}
            onChange={(event) => setBountyType(event.target.value)}
          >
            {TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {location.pathname === '/bounty/mine' && isAuthenticated ? (
          <div className="flex flex-wrap gap-1.5">
            {(['all', 'creator', 'hunter'] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  role === r
                    ? 'bg-primary text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'
                }`}
              >
                {r === 'all' ? '全部' : r === 'creator' ? '我发布的' : '我申请的'}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-48 animate-pulse rounded-xl border bg-muted/50" />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          title="加载失败"
          description={error}
          action={<Button onClick={() => window.location.reload()}>重新加载</Button>}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="暂无符合条件的悬赏"
          description="调整筛选条件，或发布一个新任务。"
          action={<Button onClick={() => navigate('/bounty/create')}>发布悬赏</Button>}
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <BountyCard key={item.id} bounty={item} onClick={() => navigate(`/bounty/${item.id}`)} />
          ))}
        </div>
      )}
    </div>
  )
}
