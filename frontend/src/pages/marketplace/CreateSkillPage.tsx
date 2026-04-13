import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload } from 'lucide-react'
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

const MAX_PACKAGE_SIZE = 10 * 1024 * 1024 // 10 MB

export default function CreateSkillPage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState({
    name: '',
    description: '',
    category: 'CODE_DEV',
    tags: [] as string[],
    pricing_model: 'FREE' as 'FREE' | 'PAID',
    price: '',
    changelog: '',
  })
  const [packageFile, setPackageFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
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

  const handleFile = useCallback((file: File) => {
    if (!file.name.endsWith('.zip')) {
      setError('请上传 .zip 格式的文件')
      return
    }
    if (file.size > MAX_PACKAGE_SIZE) {
      setError(`文件大小不能超过 ${MAX_PACKAGE_SIZE / 1024 / 1024} MB`)
      return
    }
    setPackageFile(file)
    setError('')
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    if (!form.name || !form.description) {
      setError('请补全技能名称和简介')
      return
    }
    if (!packageFile) {
      setError('请上传 Skill 包（.zip）')
      return
    }
    if (form.pricing_model === 'PAID' && (!form.price || Number(form.price) < 0.01 || Number(form.price) > 10)) {
      setError('付费 Skill 的价格范围为 $0.01 ~ $10.00')
      return
    }

    setSubmitting(true)
    try {
      const created = await createSkill({
        name: form.name,
        description: form.description,
        category: form.category,
        tags: form.tags,
        pricing_model: form.pricing_model,
        price: form.pricing_model === 'PAID' && form.price ? Number(form.price) : undefined,
        changelog: form.changelog || undefined,
        package_file: packageFile,
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
          <label className="text-sm font-medium mb-1 block">Skill 包 (.zip) *</label>
          <div
            className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
              dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
            {packageFile ? (
              <div className="text-center">
                <p className="font-medium">{packageFile.name}</p>
                <p className="text-sm text-muted-foreground">{(packageFile.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div className="text-center">
                <p className="font-medium">拖放 .zip 文件到这里，或点击选择</p>
                <p className="text-sm text-muted-foreground">ZIP 包需包含 SKILL.md，最大 10 MB</p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFile(file)
              }}
            />
          </div>
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
            {(['FREE', 'PAID'] as const).map(m => (
              <Button key={m} type="button" variant={form.pricing_model === m ? 'default' : 'outline'} size="sm"
                onClick={() => setField('pricing_model', m)}>
                {m === 'FREE' ? '免费' : '一次性购买'}
              </Button>
            ))}
          </div>
          {form.pricing_model === 'PAID' && (
            <Input
              className="mt-2 w-40"
              type="number"
              step="0.01"
              min="0.01"
              max="10"
              value={form.price}
              onChange={e => setField('price', e.target.value)}
              placeholder="价格 ($)"
            />
          )}
        </div>
        <div>
          <label className="text-sm font-medium mb-1 block">变更日志（可选）</label>
          <Textarea
            value={form.changelog}
            onChange={e => setField('changelog', e.target.value)}
            placeholder="描述此版本的变更内容"
            rows={2}
          />
        </div>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</div>}
        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? '提交中...' : '提交审核'}
        </Button>
      </form>
    </div>
  )
}
