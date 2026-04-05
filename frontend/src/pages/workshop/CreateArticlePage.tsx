import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { TagInput } from '@/components/shared/tag-input'
import { ArticleEditor, DEFAULT_ARTICLE_TEMPLATE } from '@/components/workshop/ArticleEditor'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/hooks/use-auth'
import { getMySkills, type SkillSummary } from '@/lib/skills'
import { createArticle, publishArticle } from '@/lib/workshop'

export default function CreateArticlePage() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuth()
  const [skills, setSkills] = useState<SkillSummary[]>([])
  const [form, setForm] = useState({
    title: '',
    difficulty: 'BEGINNER',
    article_type: 'TUTORIAL',
    model_tags: ['Claude Code'],
    custom_tags: [] as string[],
    related_skill_id: '',
    content: DEFAULT_ARTICLE_TEMPLATE,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, isLoading, navigate])

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

  const handleSubmit = async (e: React.FormEvent, publishImmediately: boolean) => {
    e.preventDefault()
    if (!form.title || !form.content) return

    setSubmitting(true)
    setError('')
    try {
      const article = await createArticle({
        title: form.title,
        content: form.content,
        difficulty: form.difficulty as 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED',
        article_type: form.article_type as 'TUTORIAL' | 'CASE_STUDY' | 'PITFALL' | 'REVIEW' | 'DISCUSSION',
        model_tags: form.model_tags,
        custom_tags: form.custom_tags,
        related_skill_id: form.related_skill_id ? Number(form.related_skill_id) : null,
      })

      const finalArticle = publishImmediately ? await publishArticle(article.id) : article
      navigate(`/workshop/${finalArticle.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || '文章创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/workshop')}>
          ← 返回工坊
        </Button>
        <div className="text-sm text-muted-foreground">建议先存草稿，再检查结构与标签后发布</div>
      </div>

      <div className="mb-8 max-w-3xl space-y-3">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">写一篇可复用的解决方案文章</h1>
        <p className="text-sm leading-6 text-slate-600">
          Phase 1 的文章默认围绕 Problem / Solution / Result 三段展开。发布前会校验结构和最小内容长度。
        </p>
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
                <label className="mb-2 block text-sm font-medium">正文</label>
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
              <div className="rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
                发布要求：
                <div>标题 5-120 字，正文至少 500 字。</div>
                <div>正文需包含“问题 / 方案 / 效果”三个核心段落。</div>
                <div>至少选择 1 个模型标签，自定义标签最多 5 个。</div>
              </div>
              {error ? <div className="text-sm text-rose-600">{error}</div> : null}
              <div className="flex flex-col gap-3">
                <Button
                  type="submit"
                  variant="outline"
                  disabled={submitting}
                  onClick={(event) => handleSubmit(event, false)}
                >
                  {submitting ? '处理中...' : '保存草稿'}
                </Button>
                <Button
                  type="submit"
                  disabled={submitting}
                  onClick={(event) => handleSubmit(event, true)}
                >
                  {submitting ? '处理中...' : '创建并发布'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </div>
  )
}
