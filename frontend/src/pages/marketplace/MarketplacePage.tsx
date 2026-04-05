import { useDeferredValue, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
            system_prompt: '',
            user_prompt_template: '',
            output_format: 'text',
            example_input: '',
            example_output: '',
            status: 'APPROVED',
            is_featured: false,
            current_version: 1,
            rejection_reason: '',
            creator_id: 0,
            created_at: '',
            updated_at: '',
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
    <div className="max-w-5xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">技能市场</h1>
        <Button onClick={() => navigate('/marketplace/create')}>+ 上架技能</Button>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        <Input
          placeholder="搜索技能..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-56"
        />
        <select
          className="rounded-md border bg-background px-3 py-2 text-sm"
          value={sort}
          onChange={(e) => setSort(e.target.value as (typeof SORT_OPTIONS)[number]['value'])}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              按{option.label}排序
            </option>
          ))}
        </select>
        {CATEGORIES.map(c => (
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

      {trendingSkills.length > 0 && !deferredQuery ? (
        <section className="mb-6 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">热门榜</h2>
            <span className="text-sm text-muted-foreground">按调用量、评分和精选优先级综合排序</span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {trendingSkills.map((skill) => (
              <SkillCard key={`trending-${skill.id}`} skill={skill} onClick={() => navigate(`/marketplace/${skill.id}`)} />
            ))}
          </div>
        </section>
      ) : null}

      {error ? (
        <EmptyState
          title="技能列表加载失败"
          description={error}
          action={
            <Button variant="outline" onClick={() => window.location.reload()}>
              重新加载
            </Button>
          }
        />
      ) : loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkillCardSkeleton key={index} />
          ))}
        </div>
      ) : skills.length === 0 ? (
        <EmptyState
          title="还没有符合条件的 Skill"
          description="先调整筛选条件，或者成为第一个发布者。"
          action={
            <Button onClick={() => navigate('/marketplace/create')}>
              创建 Skill
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
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
