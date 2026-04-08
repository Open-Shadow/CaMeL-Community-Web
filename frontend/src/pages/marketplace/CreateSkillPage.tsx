import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { TagInput } from '@/components/shared/tag-input'
import { createSkill, submitSkill } from '@/lib/skills'
import { useAuth } from '@/hooks/use-auth'

const CATEGORIES = [
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

export default function CreateSkillPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()
  const [form, setForm] = useState({
    name: '',
    description: '',
    system_prompt: '',
    category: 'CODE_DEV',
    tags: [] as string[],
    pricing_model: 'FREE' as 'FREE' | 'PER_USE',
    price_per_use: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

  const setField = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    if (!form.name || !form.description || !form.system_prompt) {
      setError('请补全技能名称、skill简介和skill文件')
      return
    }

    setSubmitting(true)
    try {
      const created = await createSkill({
        name: form.name,
        description: form.description,
        system_prompt: form.system_prompt,
        category: form.category,
        tags: form.tags,
        pricing_model: form.pricing_model,
        price_per_use:
          form.pricing_model === 'PER_USE' && form.price_per_use
            ? Number(form.price_per_use)
            : null,
      })

      const submitted = await submitSkill(created.id)
      navigate(`/marketplace/${submitted.id}`)
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Skill 创建失败'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading || !isAuthenticated) {
    return <div className="py-12 text-center text-sm text-muted-foreground">加载中...</div>
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/marketplace')}>← 返回</Button>
      <h1 className="text-2xl font-bold mb-6">上架技能</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-1 block">技能名称 *</label>
          <Input value={form.name} onChange={e => setField('name', e.target.value)} placeholder="简洁描述技能功能" required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">简介 *</label>
          <Textarea value={form.description} onChange={e => setField('description', e.target.value)} placeholder="描述技能的用途和效果" rows={2} required />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">skill文件 *</label>
          <Textarea
            value={form.system_prompt}
            onChange={e => setField('system_prompt', e.target.value)}
            placeholder="填写 skill 的核心执行内容"
            rows={6}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">分类</label>
          <select className="w-full border rounded-md px-3 py-2 text-sm bg-background"
            value={form.category} onChange={e => setField('category', e.target.value)}>
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">标签</label>
          <TagInput
            value={form.tags}
            onChange={(tags) => setField('tags', tags)}
            placeholder="输入标签后回车确认"
          />
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">定价模式</label>
          <div className="flex gap-3">
            {(['FREE', 'PER_USE'] as const).map(m => (
              <Button key={m} type="button" variant={form.pricing_model === m ? 'default' : 'outline'} size="sm"
                onClick={() => setField('pricing_model', m)}>
                {m === 'FREE' ? '免费' : '按次付费'}
              </Button>
            ))}
          </div>
          {form.pricing_model === 'PER_USE' && (
            <Input
              className="mt-2 w-40"
              type="number"
              step="0.01"
              min="0.01"
              max="10"
              value={form.price_per_use}
              onChange={e => setField('price_per_use', e.target.value)}
              placeholder="每次价格 ($)"
            />
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Phase 1 先打通创建、审核和调用链路，付费结算会在后续阶段接入。
          </p>
        </div>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '提交中...' : '提交审核'}
        </Button>
      </form>
    </div>
  )
}
