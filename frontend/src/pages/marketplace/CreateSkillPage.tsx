import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

const CATEGORIES = [
  { value: 'CODE_DEV', label: '代码开发' },
  { value: 'WRITING', label: '文案写作' },
  { value: 'DATA_ANALYTICS', label: '数据分析' },
  { value: 'ACADEMIC', label: '学术研究' },
  { value: 'TRANSLATION', label: '翻译' },
  { value: 'CREATIVE', label: '创意设计' },
  { value: 'AGENT', label: 'Agent 工具' },
  { value: 'PRODUCTIVITY', label: '办公效率' },
]

export default function CreateSkillPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '', description: '', system_prompt: '',
    category: 'CODE_DEV', tags: '', pricing_model: 'FREE', price_per_use: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || !form.description || !form.system_prompt) return
    setSubmitting(true)
    await new Promise(r => setTimeout(r, 600))
    setSubmitting(false)
    navigate('/marketplace')
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/marketplace')}>← 返回</Button>
      <h1 className="text-2xl font-bold mb-6">上架技能</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1 block">技能名称 *</label>
          <Input value={form.name} onChange={e => set('name', e.target.value)} placeholder="简洁描述技能功能" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">简介 *</label>
          <Textarea value={form.description} onChange={e => set('description', e.target.value)} placeholder="描述技能的用途和效果" rows={2} required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">System Prompt *</label>
          <Textarea value={form.system_prompt} onChange={e => set('system_prompt', e.target.value)} placeholder="定义 AI 的角色和行为规则" rows={5} required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">分类</label>
          <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
            value={form.category} onChange={e => set('category', e.target.value)}>
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">标签（逗号分隔）</label>
          <Input value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="Python, 数据分析, 可视化" />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">定价模式</label>
          <div className="flex gap-3">
            {['FREE', 'PER_USE'].map(m => (
              <Button key={m} type="button" variant={form.pricing_model === m ? 'default' : 'outline'} size="sm"
                onClick={() => set('pricing_model', m)}>
                {m === 'FREE' ? '免费' : '按次付费'}
              </Button>
            ))}
          </div>
          {form.pricing_model === 'PER_USE' && (
            <Input className="mt-2 w-40" type="number" step="0.01" min="0.01" max="10"
              value={form.price_per_use} onChange={e => set('price_per_use', e.target.value)}
              placeholder="每次价格 ($)" />
          )}
        </div>
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '提交中...' : '提交审核'}
        </Button>
      </form>
    </div>
  )
}
