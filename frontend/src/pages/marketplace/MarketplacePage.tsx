import { useDeferredValue, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import SkillCard from '@/components/skill/SkillCard'
import { EmptyState } from '@/components/shared/empty-state'
import { SkillCardSkeleton } from '@/components/shared/loading-skeleton'
import { listSkills, listTrendingSkills, searchSkills, type SkillSummary } from '@/lib/skills'

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

const SORT_OPTIONS = [
  { value: 'latest', label: '最新' },
  { value: 'calls', label: '调用量' },
  { value: 'rating', label: '评分' },
  { value: 'featured', label: '精选优先' },
] as const

export default function MarketplacePage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [sort, setSort] = useState<(typeof SORT_OPTIONS)[number]['value']>('latest')
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [trendingSkills, setTrendingSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const loadTrending = async () => {
      try {
        const items = await listTrendingSkills(4)
        if (active) {
          setTrendingSkills(items.map((item) => ({
            ...item,
            tags: [],
            status: 'APPROVED' as const,
            is_featured: false,
            current_version: '1.0.0',
            rejection_reason: '',
            readme_html: '',
            package_size: 0,
            download_count: 0,
            creator_id: 0,
            created_at: '',
            updated_at: '',
            has_purchased: false,
          })))
        }
      } catch {
        if (active) setTrendingSkills([])
      }
    }
    loadTrending()
    return () => {
      active = false
    }
  }, [])

  const deferredQuery = useDeferredValue(q)

  useEffect(() => {
    let active = true

    const fetchSkills = async () => {
      setLoading(true)
      setError('')
      try {
        const data = deferredQuery
          ? (await searchSkills({
              category: category || undefined,
              q: deferredQuery || undefined,
              limit: 50,
            })).items
          : await listSkills({
              category: category || undefined,
              sort,
            })
        if (active) setSkills(data)
      } catch (err: any) {
        if (active) {
          setError(err.response?.data?.detail || '技能列表加载失败')
          setSkills([])
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchSkills()

    return () => {
      active = false
    }
  }, [category, deferredQuery, sort])

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">技能市场</h1>
          <p className="mt-1 text-sm text-muted-foreground">发现、购买和使用社区创建的 AI Skill</p>
        </div>
        <Button onClick={() => navigate('/marketplace/create')}>
          <Plus className="mr-1.5 h-4 w-4" />
          上架技能
        </Button>
      </div>

      <div className="mb-6 space-y-3 rounded-xl border bg-card p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="搜索技能名称、描述..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
            value={sort}
            onChange={(e) => setSort(e.target.value as (typeof SORT_OPTIONS)[number]['value'])}
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                按{option.label}排序
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map(c => (
            <button
              key={c.value}
              type="button"
              onClick={() => setCategory(c.value)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                category === c.value
                  ? 'bg-primary text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {trendingSkills.length > 0 && !deferredQuery ? (
        <section className="mb-8 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">热门榜</h2>
            <span className="text-xs text-muted-foreground">综合排序</span>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {trendingSkills.map((skill) => (
              <SkillCard key={`trending-${skill.id}`} skill={skill} onClick={() => navigate(`/marketplace/${skill.id}`)} />
            ))}
          </div>
        </section>
      ) : null}

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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkillCardSkeleton key={index} />
          ))}
        </div>
      ) : skills.length === 0 ? (
        <EmptyState
          title="暂无符合条件的 Skill"
          description="调整筛选条件，或成为第一个发布者。"
          action={
            <Button onClick={() => navigate('/marketplace/create')}>
              创建 Skill
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {skills.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              onClick={() => navigate(`/marketplace/${skill.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
