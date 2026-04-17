import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Upload } from 'lucide-react'

import { TagInput } from '@/components/shared/tag-input'
import { ArticleEditor } from '@/components/workshop/ArticleEditor'
import { DetailSkeleton } from '@/components/shared/loading-skeleton'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/use-auth'
import { getMySkills, type SkillSummary } from '@/lib/skills'
import { getArticle, updateArticle, publishArticle, type ArticleDetail } from '@/lib/workshop'
import { markdownToHtml, readMarkdownFile } from '@/lib/markdown'

export default function EditArticlePage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { isAuthenticated, isLoading, user } = useAuth()
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [article, setArticle] = useState<ArticleDetail | null>(null)
  const [form, setForm] = useState({
    title: '',
    difficulty: 'BEGINNER',
    article_type: 'TUTORIAL',
    model_tags: [] as string[],
    custom_tags: [] as string[],
    related_skill_id: '',
    content: '',
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleImportMd = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const md = await readMarkdownFile(file)
      const html = markdownToHtml(md)
      set('content', html)
    } catch {
      setError('Markdown 文件读取失败')
    }
    e.target.value = ''
  }

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

  useEffect(() => {
    if (!id || !isAuthenticated) return
    let active = true

    const fetchArticle = async () => {
      setLoading(true)
      try {
        const data = await getArticle(Number(id))
        if (!active) return
        setArticle(data)
        setForm({
          title: data.title,
          difficulty: data.difficulty,
          article_type: data.article_type,
          model_tags: data.model_tags,
          custom_tags: data.custom_tags,
          related_skill_id: data.related_skill?.id?.toString() || '',
          content: data.content,
        })
      } catch (err: any) {
        if (active) setError(err.response?.data?.detail || '文章加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchArticle()
    return () => {
      active = false
    }
  }, [id, isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    let active = true

    const fetchSkills = async () => {
      try {
        const items = await getMySkills()
        if (active) setSkills(items)
      } catch {
        if (active) setSkills([])
      }
    }

    fetchSkills()
    return () => {
      active = false
    }
  }, [isAuthenticated])

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !form.title) return

    setSubmitting(true)
    setError('')
    try {
      const updated = await updateArticle(Number(id), {
        title: form.title,
        content: form.content,
        difficulty: form.difficulty as 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED',
        article_type: form.article_type as 'TUTORIAL' | 'CASE_STUDY' | 'PITFALL' | 'REVIEW' | 'DISCUSSION',
        model_tags: form.model_tags,
        custom_tags: form.custom_tags,
        related_skill_id: form.related_skill_id ? Number(form.related_skill_id) : null,
      })
      setArticle(updated)
      navigate(`/workshop/${updated.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !form.title) return

    setSubmitting(true)
    setError('')
    try {
      await updateArticle(Number(id), {
        title: form.title,
        content: form.content,
        difficulty: form.difficulty as 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED',
        article_type: form.article_type as 'TUTORIAL' | 'CASE_STUDY' | 'PITFALL' | 'REVIEW' | 'DISCUSSION',
        model_tags: form.model_tags,
        custom_tags: form.custom_tags,
        related_skill_id: form.related_skill_id ? Number(form.related_skill_id) : null,
      })
      const published = await publishArticle(Number(id))
      navigate(`/workshop/${published.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '发布失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <DetailSkeleton />
      </div>
    )
  }

  if (error && !article) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <EmptyState
          title="无法加载文章"
          description={error}
          action={
            <Button variant="outline" onClick={() => navigate('/workshop')}>
              返回工坊
            </Button>
          }
        />
      </div>
    )
  }

  if (article && user && article.author.id !== user.id) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <EmptyState
          title="无权编辑"
          description="只能编辑自己的文章"
          action={
            <Button variant="outline" onClick={() => navigate('/workshop')}>
              返回工坊
            </Button>
          }
        />
      </div>
    )
  }

  const isDraft = article?.status === 'DRAFT'

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate(`/workshop/${id}`)}>
          ← 返回文章
        </Button>
        <div className="text-sm text-muted-foreground">
          {isDraft ? '编辑草稿，保存后可发布' : '编辑已发布文章'}
        </div>
      </div>

      <div className="mb-8 max-w-3xl space-y-3">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">编辑文章</h1>
      </div>

      <form className="grid gap-6 lg:grid-cols-[1.6fr_0.8fr]">
        <div className="space-y-5">
          <Card>
            <CardContent className="space-y-4 p-5">
              <div>
                <label className="mb-2 block text-sm font-medium">标题</label>
                <Input
                  value={form.title}
                  onChange={(event) => set('title', event.target.value)}
                  placeholder="例如：用 Claude Code 三步搭建可复用 MCP Server"
                  required
                />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="block text-sm font-medium">正文</label>
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".md,.markdown,text/markdown"
                      className="hidden"
                      onChange={handleImportMd}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Upload className="mr-1 h-4 w-4" />
                      导入 MD
                    </Button>
                  </div>
                </div>
                <ArticleEditor value={form.content} onChange={(value) => set('content', value)} />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardContent className="space-y-4 p-5">
              <h2 className="text-lg font-semibold">发布信息</h2>
              <div>
                <label className="mb-2 block text-sm font-medium">难度</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={form.difficulty}
                  onChange={(event) => set('difficulty', event.target.value)}
                >
                  <option value="BEGINNER">入门</option>
                  <option value="INTERMEDIATE">进阶</option>
                  <option value="ADVANCED">高级</option>
                </select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">类型</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={form.article_type}
                  onChange={(event) => set('article_type', event.target.value)}
                >
                  <option value="TUTORIAL">教程</option>
                  <option value="CASE_STUDY">案例</option>
                  <option value="PITFALL">踩坑记录</option>
                  <option value="REVIEW">评测</option>
                  <option value="DISCUSSION">讨论</option>
                </select>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">模型标签</label>
                <TagInput
                  value={form.model_tags}
                  onChange={(tags) => set('model_tags', tags)}
                  maxTags={5}
                  placeholder="输入模型标签，例如 Claude Code"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">自定义标签</label>
                <TagInput
                  value={form.custom_tags}
                  onChange={(tags) => set('custom_tags', tags)}
                  maxTags={5}
                  placeholder="输入主题标签，例如 MCP"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium">关联 Skill</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={form.related_skill_id}
                  onChange={(event) => set('related_skill_id', event.target.value)}
                >
                  <option value="">暂不关联</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="rounded-xl bg-muted p-4 text-sm leading-6 text-muted-foreground">
                发布要求：
                <div>标题 5-120 字。</div>
                <div>至少选择 1 个模型标签，自定义标签最多 5 个。</div>
              </div>
              {error ? <div className="text-sm text-rose-600">{error}</div> : null}
              <div className="flex flex-col gap-3">
                <Button
                  type="submit"
                  variant="outline"
                  disabled={submitting}
                  onClick={handleSave}
                >
                  {submitting ? '处理中...' : '保存'}
                </Button>
                {isDraft ? (
                  <Button
                    type="submit"
                    disabled={submitting}
                    onClick={handlePublish}
                  >
                    {submitting ? '处理中...' : '保存并发布'}
                  </Button>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </div>
  )
}
