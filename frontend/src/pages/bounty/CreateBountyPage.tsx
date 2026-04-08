import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { createBounty } from '@/lib/bounties'
import { useAuth } from '@/hooks/use-auth'

export default function CreateBountyPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [form, setForm] = useState({
    title: '',
    description: '',
    attachments: '',
    skill_requirements: '',
    type: 'SKILL_CUSTOM',
    max_applicants: '1',
    workload_estimate: 'ONE_TO_TWO_HOURS',
    reward: '',
    deadline: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isAuthenticated) {
      setMessage('请先登录后再发布悬赏')
      return
    }

    const title = form.title.trim()
    const reward = Number(form.reward)
    const maxApplicants = Number(form.max_applicants)
    if (!title) {
      setMessage('请填写悬赏标题')
      return
    }
    if (!Number.isFinite(reward) || reward < 1) {
      setMessage('赏金金额需不低于 $1.00')
      return
    }
    if (!form.deadline) {
      setMessage('请选择截止日期')
      return
    }
    if (!Number.isFinite(maxApplicants) || maxApplicants < 1 || maxApplicants > 20) {
      setMessage('最大申请人数需在 1 到 20 之间')
      return
    }

    const deadlineDate = new Date(`${form.deadline}T23:59:59`)
    if (Number.isNaN(deadlineDate.getTime())) {
      setMessage('截止日期格式无效')
      return
    }

    setSubmitting(true)
    setMessage('')
    try {
      const bounty = await createBounty({
        title,
        description: form.description,
        attachments: form.attachments
          .split('\n')
          .map((item) => item.trim())
          .filter(Boolean),
        skill_requirements: form.skill_requirements,
        bounty_type: form.type,
        max_applicants: maxApplicants,
        workload_estimate: form.workload_estimate,
        reward,
        deadline: deadlineDate.toISOString(),
      })
      navigate(`/bounty/${bounty.id}`)
    } catch (error: any) {
      const data = error?.response?.data
      const detailText =
        (typeof data?.message === 'string' && data.message) ||
        (typeof data?.detail === 'string' && data.detail) ||
        (Array.isArray(data?.detail) && data.detail[0]?.msg) ||
        ''
      const status = error?.response?.status
      setMessage(detailText || (status ? `发布失败（HTTP ${status}）` : '发布失败（网络异常）'))
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/bounty')}>← 返回</Button>
      <h1 className="text-2xl font-bold mb-6">发布悬赏</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1 block">标题 *</label>
          <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="简洁描述需求" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">详细描述</label>
          <Textarea value={form.description} onChange={e => set('description', e.target.value)}
            placeholder="描述需求背景、交付物要求、验收标准..." rows={5} />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">附件链接（可选）</label>
          <Textarea
            value={form.attachments}
            onChange={e => set('attachments', e.target.value)}
            placeholder="每行一个链接，例如交互原型、示例文件等"
            rows={3}
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">类型</label>
          <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
            value={form.type} onChange={e => set('type', e.target.value)}>
            <option value="SKILL_CUSTOM">Skill 定制</option>
            <option value="DATA_PROCESSING">数据处理</option>
            <option value="CONTENT_CREATION">内容创作</option>
            <option value="BUG_FIX">问题修复</option>
            <option value="GENERAL">通用任务</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">技能要求（可选）</label>
          <Textarea
            value={form.skill_requirements}
            onChange={e => set('skill_requirements', e.target.value)}
            placeholder="例如：熟悉 Claude Code、Python、日志分析"
            rows={3}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium mb-1 block">最大申请人数</label>
            <Input
              type="number"
              min="1"
              max="20"
              step="1"
              value={form.max_applicants}
              onChange={e => set('max_applicants', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">预计工作量</label>
            <select
              className="w-full border rounded-md px-3 py-2 text-sm bg-background"
              value={form.workload_estimate}
              onChange={e => set('workload_estimate', e.target.value)}
            >
              <option value="ONE_TO_TWO_HOURS">1~2小时</option>
              <option value="HALF_DAY">半天</option>
              <option value="ONE_DAY">1天</option>
              <option value="TWO_TO_THREE_DAYS">2~3天</option>
              <option value="ONE_WEEK_PLUS">1周以上</option>
            </select>
          </div>
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">赏金 ($) *</label>
          <Input type="number" min="1" step="0.01" value={form.reward}
            onChange={e => set('reward', e.target.value)} placeholder="最低 $1.00" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">截止日期 *</label>
          <Input type="date" value={form.deadline} onChange={e => set('deadline', e.target.value)} required />
        </div>
        {message ? <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{message}</div> : null}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '发布中...' : '发布悬赏'}
        </Button>
      </form>
    </div>
  )
}
