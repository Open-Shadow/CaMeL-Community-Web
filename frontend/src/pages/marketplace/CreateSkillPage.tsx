import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { TagInput } from '@/components/shared/tag-input'
import { createSkill, submitSkill } from '@/lib/skills'
import { useAuth } from '@/hooks/use-auth'
import { unzipSync, strFromU8 } from 'fflate'

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
  const [skillMdPreview, setSkillMdPreview] = useState<{ frontmatter: Record<string, unknown>; body: string } | null>(null)
  const [previewExpanded, setPreviewExpanded] = useState(true)

  /** Parse SKILL.md from a ZIP file and extract frontmatter + body. */
  const parseSkillMd = useCallback(async (file: File) => {
    try {
      const buffer = await file.arrayBuffer()
      const unzipped = unzipSync(new Uint8Array(buffer))

      // Find SKILL.md — at root or in a single top-level directory
      let skillMdContent: string | null = null
      const paths = Object.keys(unzipped)
      const directMatch = paths.find(
        (p) => p === 'SKILL.md' || p.endsWith('/SKILL.md'),
      )
      if (directMatch) {
        skillMdContent = strFromU8(unzipped[directMatch])
      }

      if (!skillMdContent) {
        setSkillMdPreview(null)
        return
      }

      // Parse YAML frontmatter
      if (!skillMdContent.startsWith('---')) {
        setSkillMdPreview({ frontmatter: {}, body: skillMdContent })
        return
      }

      const parts = skillMdContent.split('---')
      if (parts.length < 3) {
        setSkillMdPreview({ frontmatter: {}, body: skillMdContent })
        return
      }

      // Simple YAML parser for frontmatter (key: value pairs)
      const yamlBlock = parts[1]
      const frontmatter: Record<string, unknown> = {}
      for (const line of yamlBlock.split('\n')) {
        const match = line.match(/^(\w+)\s*:\s*(.+)$/)
        if (match) {
          const value = match[2].trim()
          // Handle arrays like [tag1, tag2]
          if (value.startsWith('[') && value.endsWith(']')) {
            frontmatter[match[1]] = value
              .slice(1, -1)
              .split(',')
              .map((s) => s.trim().replace(/^['"]|['"]$/g, ''))
              .filter(Boolean)
          } else {
            frontmatter[match[1]] = value.replace(/^['"]|['"]$/g, '')
          }
        }
      }

      const body = parts.slice(2).join('---').trim()
      setSkillMdPreview({ frontmatter, body })

      // Auto-fill form fields from frontmatter
      setForm((current) => {
        const updated = { ...current }
        if (frontmatter.name && typeof frontmatter.name === 'string' && !current.name) {
          updated.name = frontmatter.name
        }
        if (frontmatter.description && typeof frontmatter.description === 'string' && !current.description) {
          updated.description = frontmatter.description
        }
        if (frontmatter.category && typeof frontmatter.category === 'string') {
          const validCat = CATEGORIES.find((c) => c.value === frontmatter.category)
          if (validCat) updated.category = validCat.value
        }
        if (Array.isArray(frontmatter.tags) && current.tags.length === 0) {
          updated.tags = frontmatter.tags as string[]
        }
        return updated
      })
    } catch {
      setSkillMdPreview(null)
    }
  }, [])

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
    parseSkillMd(file)
  }, [parseSkillMd])

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

        {skillMdPreview && (
          <div className="rounded-lg border bg-muted/30 p-4">
            <button
              type="button"
              className="flex w-full items-center justify-between text-sm font-medium"
              onClick={() => setPreviewExpanded(!previewExpanded)}
            >
              <span className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                SKILL.md 预览
                {skillMdPreview.frontmatter.version != null && (
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs">
                    v{String(skillMdPreview.frontmatter.version)}
                  </span>
                )}
              </span>
              {previewExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            {previewExpanded && (
              <div className="mt-3 space-y-3">
                {Object.keys(skillMdPreview.frontmatter).length > 0 && (
                  <div className="rounded border bg-background p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">Frontmatter</p>
                    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                      {Object.entries(skillMdPreview.frontmatter).map(([key, value]) => (
                        <div key={key} className="contents">
                          <dt className="font-medium text-muted-foreground">{key}:</dt>
                          <dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                )}
                {skillMdPreview.body && (
                  <div className="rounded border bg-background p-3">
                    <p className="mb-2 text-xs font-medium text-muted-foreground">README</p>
                    <div className="prose prose-sm max-h-64 overflow-auto whitespace-pre-wrap text-sm">
                      {skillMdPreview.body}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

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
