import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export default function CreateBountyPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ title: '', description: '', type: 'DEV', reward: '', deadline: '' })
  const [submitting, setSubmitting] = useState(false)
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title || !form.reward) return
    setSubmitting(true)
    await new Promise(r => setTimeout(r, 500))
    setSubmitting(false)
    navigate('/bounty')
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
            <option value="DEV">开发</option>
            <option value="DESIGN">设计</option>
            <option value="WRITING">写作</option>
            <option value="TRANSLATION">翻译</option>
            <option value="DATA">数据</option>
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
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '发布中...' : '发布悬赏'}
        </Button>
      </form>
    </div>
  )
}
