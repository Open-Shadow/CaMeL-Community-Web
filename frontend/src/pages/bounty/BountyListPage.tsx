import { useDeferredValue, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

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
    <div className="mx-auto max-w-6xl px-4 py-8">
      <section className="mb-8 rounded-[28px] bg-gradient-to-br from-emerald-50 via-white to-sky-50 p-6 shadow-sm ring-1 ring-slate-200">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl space-y-3">
            <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
              Bounty Board
            </span>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">悬赏任务板</h1>
            <p className="text-sm leading-6 text-slate-600">
              发布明确需求，托管赏金，接受交付，并在必要时进入社区仲裁。
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link to="/bounty/mine">我的悬赏</Link>
            </Button>
            <Button onClick={() => navigate('/bounty/create')}>发布悬赏</Button>
          </div>
        </div>
      </section>

      <section className="mb-8 space-y-4 rounded-3xl border bg-white p-5">
        <div className="grid gap-3 lg:grid-cols-3">
          <Input
            placeholder="搜索悬赏标题或描述..."
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />
          <select
            className="rounded-md border bg-background px-3 py-2 text-sm"
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
            className="rounded-md border bg-background px-3 py-2 text-sm"
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
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant={role === 'all' ? 'default' : 'outline'} onClick={() => setRole('all')}>
              全部
            </Button>
            <Button size="sm" variant={role === 'creator' ? 'default' : 'outline'} onClick={() => setRole('creator')}>
              我发布的
            </Button>
            <Button size="sm" variant={role === 'hunter' ? 'default' : 'outline'} onClick={() => setRole('hunter')}>
              我申请的
            </Button>
          </div>
        ) : null}
      </section>

      {loading ? (
        <div className="py-12 text-center text-muted-foreground">加载悬赏中...</div>
      ) : error ? (
        <EmptyState
          title="悬赏列表加载失败"
          description={error}
          action={<Button onClick={() => window.location.reload()}>重新加载</Button>}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="当前没有符合条件的悬赏"
          description="调整筛选条件，或者直接发布一个新任务。"
          action={<Button onClick={() => navigate('/bounty/create')}>发布悬赏</Button>}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <BountyCard key={item.id} bounty={item} onClick={() => navigate(`/bounty/${item.id}`)} />
          ))}
        </div>
      )}
    </div>
  )
}
