import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { createBounty } from '@/lib/bounties'

export default function CreateBountyPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    title: '',
    description: '',
    type: 'SKILL_CUSTOM',
    reward: '',
    deadline: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title || !form.reward) return
    setSubmitting(true)
    setMessage('')
    try {
      const bounty = await createBounty({
        title: form.title,
        description: form.description,
        bounty_type: form.type,
        reward: Number(form.reward),
        deadline: new Date(form.deadline).toISOString(),
      })
      navigate(`/bounty/${bounty.id}`)
    } catch (error: any) {
      setMessage(error.response?.data?.message || '发布失败')
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
          <label className="text-sm font-medium mb-1 block">赏金 ($) *</label>
          <Input type="number" min="1" step="0.01" value={form.reward}
            onChange={e => set('reward', e.target.value)} placeholder="最低 $1.00" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">截止日期</label>
          <Input type="date" value={form.deadline} onChange={e => set('deadline', e.target.value)} />
        </div>
        {message ? <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{message}</div> : null}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '发布中...' : '发布悬赏'}
        </Button>
      </form>
    </div>
  )
}
