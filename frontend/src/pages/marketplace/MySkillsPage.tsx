import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import SkillCard from '@/components/skill/SkillCard'
import { EmptyState } from '@/components/shared/empty-state'
import { SkillCardSkeleton } from '@/components/shared/loading-skeleton'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api, useAuth } from '@/hooks/use-auth'
import { formatCurrency } from '@/lib/utils'
import {
  archiveSkill,
  deleteSkill,
  getSkillIncomeDashboard,
  restoreSkill,
  type SkillIncomeDashboard,
  type SkillSummary,
} from '@/lib/skills'

const STATUS_LABELS: Record<string, string> = {
  DRAFT: '草稿',
  PENDING_REVIEW: '待审核',
  APPROVED: '已上架',
  REJECTED: '已拒绝',
  ARCHIVED: '已归档',
}

export default function MySkillsPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<string>('ALL')
  const [income, setIncome] = useState<SkillIncomeDashboard | null>(null)
  const [actioningId, setActioningId] = useState<number | null>(null)

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

  useEffect(() => {
    if (!isAuthenticated) return

    let active = true
    const fetchMySkills = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await api.get<SkillSummary[]>('/skills/mine')
        const incomeResponse = await getSkillIncomeDashboard().catch(() => null)
        if (!active) return
        setSkills(response.data)
        setIncome(incomeResponse)
      } catch (err: any) {
        if (!active) return
        setError(err.response?.data?.detail || '我的 Skill 列表加载失败')
        setSkills([])
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchMySkills()
    return () => {
      active = false
    }
  }, [isAuthenticated])

  if (isLoading || !isAuthenticated) {
    return <div className="py-12 text-center text-sm text-muted-foreground">加载中...</div>
  }

  const filteredSkills =
    status === 'ALL' ? skills : skills.filter((skill) => skill.status === status)

  const refreshIncome = async () => {
    setIncome(await getSkillIncomeDashboard().catch(() => null))
  }

  const handleArchive = async (skillId: number) => {
    setError('')
    setActioningId(skillId)
    try {
      const updated = await archiveSkill(skillId)
      setSkills((current) => current.map((item) => (item.id === skillId ? updated : item)))
      await refreshIncome()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.response?.data?.message || 'Skill 下架失败')
    } finally {
      setActioningId(null)
    }
  }

  const handleRestore = async (skillId: number) => {
    setError('')
    setActioningId(skillId)
    try {
      const updated = await restoreSkill(skillId)
      setSkills((current) => current.map((item) => (item.id === skillId ? updated : item)))
      await refreshIncome()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.response?.data?.message || 'Skill 恢复失败')
    } finally {
      setActioningId(null)
    }
  }

  const handleDelete = async (skill: SkillSummary) => {
    const confirmed = window.confirm(`确认删除 Skill「${skill.name}」吗？删除后无法恢复。`)
    if (!confirmed) return

    setError('')
    setActioningId(skill.id)
    try {
      await deleteSkill(skill.id)
      setSkills((current) => current.filter((item) => item.id !== skill.id))
      await refreshIncome()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.response?.data?.message || 'Skill 删除失败')
    } finally {
      setActioningId(null)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">我的 Skill</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            管理你的草稿、审核状态和已上架 Skill。
          </p>
        </div>
        <Button onClick={() => navigate('/marketplace/create')}>创建新 Skill</Button>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={status === 'ALL' ? 'default' : 'outline'}
          onClick={() => setStatus('ALL')}
        >
          全部
        </Button>
        {Object.entries(STATUS_LABELS).map(([key, label]) => (
          <Button
            key={key}
            size="sm"
            variant={status === key ? 'default' : 'outline'}
            onClick={() => setStatus(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {error ? (
        <EmptyState
          title="我的 Skill 列表加载失败"
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
      ) : filteredSkills.length === 0 ? (
        <EmptyState
          title="当前状态下没有 Skill"
          description="先创建一个 Skill，或者切换筛选状态。"
          action={<Button onClick={() => navigate('/marketplace/create')}>创建 Skill</Button>}
        />
      ) : (
        <div className="space-y-6">
          {income ? (
            <Card>
              <CardHeader>
                <CardTitle>创作者收入看板</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">累计收入</div>
                  <div className="mt-2 text-2xl font-semibold">{formatCurrency(income.total_income)}</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">累计调用</div>
                  <div className="mt-2 text-2xl font-semibold">{income.total_calls}</div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="text-sm text-muted-foreground">上架 Skill</div>
                  <div className="mt-2 text-2xl font-semibold">{income.skills.length}</div>
                </div>
              </CardContent>
            </Card>
          ) : null}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredSkills.map((skill) => (
              <div key={skill.id} className="space-y-2">
                <SkillCard skill={skill} onClick={() => navigate(`/marketplace/${skill.id}`)} />
                <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium">{STATUS_LABELS[skill.status] || skill.status}</span>
                    <span className="text-muted-foreground">v{skill.current_version}</span>
                  </div>
                  {skill.rejection_reason ? (
                    <p className="mt-2 text-xs text-red-600">{skill.rejection_reason}</p>
                  ) : (
                    <p className="mt-2 text-xs text-muted-foreground">
                      审核状态稳定，可继续编辑后重新提交。
                    </p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {skill.status !== 'ARCHIVED' ? (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actioningId === skill.id}
                        onClick={() => handleArchive(skill.id)}
                      >
                        {actioningId === skill.id ? '处理中...' : '下架'}
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actioningId === skill.id}
                        onClick={() => handleRestore(skill.id)}
                      >
                        {actioningId === skill.id ? '处理中...' : '恢复为草稿'}
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={actioningId === skill.id}
                      onClick={() => handleDelete(skill)}
                    >
                      {actioningId === skill.id ? '处理中...' : '删除'}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
