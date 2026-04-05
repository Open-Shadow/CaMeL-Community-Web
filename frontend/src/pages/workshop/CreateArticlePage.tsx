import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

export default function CreateArticlePage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ title: '', type: 'TUTORIAL', content: '', tags: '' })
  const [submitting, setSubmitting] = useState(false)
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.title || !form.content) return
    setSubmitting(true)
    await new Promise(r => setTimeout(r, 500))
    setSubmitting(false)
    navigate('/workshop')
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/workshop')}>← 返回</Button>
      <h1 className="text-2xl font-bold mb-6">写文章</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1 block">标题 *</label>
          <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="文章标题" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">类型</label>
          <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
            value={form.type} onChange={e => set('type', e.target.value)}>
            <option value="TUTORIAL">教程</option>
            <option value="CASE_STUDY">案例</option>
            <option value="PITFALL">踩坑</option>
            <option value="REVIEW">评测</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">内容 *</label>
          <Textarea value={form.content} onChange={e => set('content', e.target.value)}
            placeholder="分享你的经验..." rows={10} required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">标签（逗号分隔）</label>
          <Input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="Python, AI, 实战" />
        </div>
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '发布中...' : '发布文章'}
        </Button>
      </form>
    </div>
  )
}
