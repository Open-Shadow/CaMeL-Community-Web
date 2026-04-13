import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Flag, File as FileIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { EmptyState } from '@/components/shared/empty-state'
import { DetailSkeleton } from '@/components/shared/loading-skeleton'
import {
  addSkillReview,
  archiveSkill,
  deleteSkill,
  downloadSkill,
  getSkill,
  getSkillFileTree,
  getSkillUsagePreference,
  listSkillReviews,
  listSkillVersions,
  purchaseSkill,
  reportSkill,
  restoreSkill,
  type PackageFileEntry,
  type SkillReview,
  type SkillSummary,
  type SkillUsagePreference,
  type SkillVersion,
  updateSkillUsagePreference,
} from '@/lib/skills'
import { formatCurrency, formatDate } from '@/lib/utils'
import { useAuth } from '@/hooks/use-auth'

const STATUS_BADGE: Record<string, 'default' | 'outline' | 'secondary' | 'destructive'> = {
  APPROVED: 'default',
  SCANNING: 'secondary',
  REJECTED: 'destructive',
  ARCHIVED: 'outline',
  DRAFT: 'outline',
}

const REPORT_REASONS = [
  { value: 'MALICIOUS_CODE', label: '包含恶意代码' },
  { value: 'FALSE_DESCRIPTION', label: '描述不符' },
  { value: 'COPYRIGHT', label: '版权侵权' },
  { value: 'OTHER', label: '其他' },
]

export default function SkillDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()
  const [skill, setSkill] = useState<SkillSummary | null>(null)
  const [reviews, setReviews] = useState<SkillReview[]>([])
  const [versions, setVersions] = useState<SkillVersion[]>([])
  const [usagePreference, setUsagePreference] = useState<SkillUsagePreference | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [reviewRating, setReviewRating] = useState('5')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewTags, setReviewTags] = useState('')
  const [managing, setManaging] = useState(false)
  const [purchasing, setPurchasing] = useState(false)
  const [showReportForm, setShowReportForm] = useState(false)
  const [reportReason, setReportReason] = useState('MALICIOUS_CODE')
  const [reportDetail, setReportDetail] = useState('')
  const [fileTree, setFileTree] = useState<PackageFileEntry[]>([])
  const [fileTreeLoading, setFileTreeLoading] = useState(false)

  useEffect(() => {
    let active = true
    const skillId = Number(id)

    if (!skillId) {
      setError('Skill ID 无效')
      setLoading(false)
      return
    }

    const fetchSkill = async () => {
      setLoading(true)
      setError('')
      try {
        const [data, reviewData, versionData] = await Promise.all([
          getSkill(skillId),
          listSkillReviews(skillId).catch(() => []),
          listSkillVersions(skillId).catch(() => []),
        ])
        if (!active) return
        setSkill(data)
        setReviews(reviewData)
        setVersions(versionData)
        if (isAuthenticated) {
          setUsagePreference(await getSkillUsagePreference(skillId).catch(() => null))
        }
      } catch (err: any) {
        if (active) setError(err.response?.data?.detail || 'Skill 详情加载失败')
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchSkill()

    return () => {
      active = false
    }
  }, [id, isAuthenticated])

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <DetailSkeleton />
      </div>
    )
  }

  if (error || !skill) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <EmptyState
          title="Skill 详情不可用"
          description={error || '未找到对应 Skill'}
          action={
            <Button variant="outline" onClick={() => navigate('/marketplace')}>
              返回市场
            </Button>
          }
        />
      </div>
    )
  }

  const isOwner = Boolean(isAuthenticated && user && user.id === skill.creator_id)
  const canDownload = skill.pricing_model === 'FREE' || skill.has_purchased || isOwner

  const handlePurchase = async () => {
    setPurchasing(true)
    setMessage('')
    try {
      await purchaseSkill(skill.id)
      setSkill({ ...skill, has_purchased: true })
      setMessage('购买成功！')
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || err?.response?.data?.message || '购买失败')
    } finally {
      setPurchasing(false)
    }
  }

  const handleReport = async () => {
    setMessage('')
    try {
      await reportSkill(skill.id, { reason: reportReason, detail: reportDetail })
      setMessage('举报已提交')
      setShowReportForm(false)
      setReportDetail('')
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || err?.response?.data?.message || '举报失败')
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="mx-auto max-w-7xl py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/marketplace')}>← 返回市场</Button>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,2fr)_360px]">
        <div className="space-y-6">
          <section className="rounded-[28px] border bg-white p-6 shadow-sm">
            <div className="mb-2 flex flex-wrap gap-2">
              {skill.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
              <Badge variant={STATUS_BADGE[skill.status] || 'outline'}>
                {skill.status}
              </Badge>
              {skill.is_featured && <Badge>精选</Badge>}
            </div>
            <h1 className="mb-2 text-3xl font-bold tracking-tight">{skill.name}</h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span>by {skill.creator_name}</span>
              <span>⭐ {skill.avg_rating.toFixed(1)} ({skill.review_count} 条评价)</span>
              <span>{skill.total_calls} 次调用</span>
              <span>{skill.download_count} 次下载</span>
              <span>v{skill.current_version}</span>
              <span>{formatSize(skill.package_size)}</span>
              <span>更新于 {formatDate(skill.updated_at)}</span>
              <span className="text-base font-semibold text-amber-500">
                {skill.pricing_model === 'FREE'
                  ? '免费'
                  : `${formatCurrency(skill.price)}`}
              </span>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              {!isOwner && skill.pricing_model === 'PAID' && !skill.has_purchased && (
                <Button onClick={handlePurchase} disabled={purchasing}>
                  {purchasing ? '购买中...' : `购买 ${formatCurrency(skill.price)}`}
                </Button>
              )}
              {canDownload && (
                <Button variant="outline" onClick={() => downloadSkill(skill.id)}>
                  <Download className="mr-2 h-4 w-4" /> 下载包
                </Button>
              )}
              {isAuthenticated && !isOwner && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowReportForm((v) => !v)}
                >
                  <Flag className="mr-1 h-4 w-4" /> 举报
                </Button>
              )}
            </div>
          </section>

          {skill.rejection_reason ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              审核未通过原因：{skill.rejection_reason}
            </div>
          ) : null}

          {message ? (
            <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
              {message}
            </div>
          ) : null}

          {showReportForm && (
            <Card>
              <CardContent className="space-y-3 p-4">
                <h3 className="font-semibold">举报此 Skill</h3>
                <select
                  className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                >
                  {REPORT_REASONS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
                <Textarea
                  value={reportDetail}
                  onChange={(e) => setReportDetail(e.target.value)}
                  placeholder="补充说明（可选）"
                  rows={2}
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={handleReport}>提交举报</Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowReportForm(false)}>取消</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {isOwner ? (
            <Card>
              <CardContent className="flex flex-wrap items-center gap-2 p-4">
                <span className="text-sm text-muted-foreground">创作者管理：</span>
                {skill.status !== 'ARCHIVED' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={managing}
                    onClick={async () => {
                      setManaging(true)
                      try {
                        setSkill(await archiveSkill(skill.id))
                        setMessage('已下架该 Skill')
                      } catch (err: any) {
                        setMessage(err?.response?.data?.detail || err?.response?.data?.message || '下架失败')
                      } finally {
                        setManaging(false)
                      }
                    }}
                  >
                    {managing ? '处理中...' : '下架'}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={managing}
                    onClick={async () => {
                      setManaging(true)
                      try {
                        setSkill(await restoreSkill(skill.id))
                        setMessage('已恢复为草稿，可重新提交审核')
                      } catch (err: any) {
                        setMessage(err?.response?.data?.detail || err?.response?.data?.message || '恢复失败')
                      } finally {
                        setManaging(false)
                      }
                    }}
                  >
                    {managing ? '处理中...' : '恢复为草稿'}
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={managing}
                  onClick={async () => {
                    if (!window.confirm(`确认删除 Skill「${skill.name}」吗？删除后无法恢复。`)) return
                    setManaging(true)
                    try {
                      await deleteSkill(skill.id)
                      navigate('/marketplace/mine')
                    } catch (err: any) {
                      setMessage(err?.response?.data?.detail || err?.response?.data?.message || '删除失败')
                    } finally {
                      setManaging(false)
                    }
                  }}
                >
                  {managing ? '处理中...' : '删除'}
                </Button>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardContent className="space-y-4 p-4">
              <div>
                <h2 className="mb-2 font-semibold">简介</h2>
                <div className="rounded bg-muted p-3 text-sm whitespace-pre-wrap">{skill.description}</div>
              </div>

              {skill.readme_html ? (
                <div className="border-t pt-4">
                  <h2 className="mb-3 font-semibold">README</h2>
                  <div
                    className="prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: skill.readme_html }}
                  />
                </div>
              ) : null}

              {canDownload ? (
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="font-semibold">文件列表</h2>
                    {fileTree.length === 0 && !fileTreeLoading && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          setFileTreeLoading(true)
                          try {
                            setFileTree(await getSkillFileTree(skill.id))
                          } catch {
                            // Silently fail — user can retry
                          } finally {
                            setFileTreeLoading(false)
                          }
                        }}
                      >
                        查看文件
                      </Button>
                    )}
                  </div>
                  {fileTreeLoading && (
                    <p className="text-sm text-muted-foreground">加载中...</p>
                  )}
                  {fileTree.length > 0 && (
                    <ul className="space-y-1 text-sm font-mono">
                      {fileTree
                        .filter((f) => !f.is_dir)
                        .map((f) => (
                          <li key={f.path} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-muted/50">
                            <FileIcon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="truncate">{f.path}</span>
                            <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                              {f.size < 1024
                                ? `${f.size} B`
                                : `${(f.size / 1024).toFixed(1)} KB`}
                            </span>
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              ) : skill.pricing_model === 'PAID' ? (
                <div className="border-t pt-4">
                  <h2 className="mb-3 font-semibold">文件列表</h2>
                  <p className="text-sm text-muted-foreground">
                    购买后可查看文件列表和下载包内容。
                  </p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-20">
          <Card>
            <CardContent className="space-y-4 p-4">
              <h2 className="font-semibold">版本历史</h2>
              {usagePreference ? (
                <div className="rounded-lg border bg-muted/30 p-3 text-sm">
                  {usagePreference.auto_follow_latest
                    ? '当前跟随最新版'
                    : `当前锁定版本 v${usagePreference.locked_version}`}
                </div>
              ) : null}
              {versions.length === 0 ? (
                <p className="text-sm text-muted-foreground">当前还没有更多版本记录。</p>
              ) : (
                versions.map((version) => (
                  <div key={version.id} className="rounded-lg border p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">v{version.version}</span>
                      <Badge variant={STATUS_BADGE[version.status] || 'outline'}>{version.status}</Badge>
                    </div>
                    <p className="mt-2 text-muted-foreground">{version.changelog || '版本更新'}</p>
                    <div className="mt-2 text-xs text-muted-foreground">{formatDate(version.created_at)}</div>
                    {isAuthenticated ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={async () => {
                            if (!skill) return
                            setUsagePreference(await updateSkillUsagePreference(skill.id, {
                              locked_version: version.version,
                              auto_follow_latest: false,
                            }))
                          }}
                        >
                          锁定此版本
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={async () => {
                            if (!skill) return
                            setUsagePreference(await updateSkillUsagePreference(skill.id, {
                              locked_version: null,
                              auto_follow_latest: true,
                            }))
                          }}
                        >
                          跟随最新版
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 p-4">
              <h2 className="font-semibold">用户评价</h2>
              {reviews.length === 0 ? <p className="text-sm text-muted-foreground">还没有评价。</p> : null}
              {reviews.map((review) => (
                <div key={review.id} className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{review.reviewer_name}</span>
                    <span>{'★'.repeat(review.rating)}</span>
                  </div>
                  <p className="mt-2 text-muted-foreground">{review.comment || '该用户没有填写文字评价。'}</p>
                  <div className="mt-2 text-xs text-muted-foreground">{formatDate(review.created_at)}</div>
                </div>
              ))}

              {isAuthenticated ? (
                <div className="space-y-3 border-t pt-4">
                  <div className="grid grid-cols-2 gap-3">
                    <Input type="number" min="1" max="5" value={reviewRating} onChange={(e) => setReviewRating(e.target.value)} />
                    <Input value={reviewTags} onChange={(e) => setReviewTags(e.target.value)} placeholder="标签，用逗号分隔" />
                  </div>
                  <Textarea value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} rows={3} placeholder="写下实际体验..." />
                  <Button
                    variant="outline"
                    onClick={async () => {
                      if (!skill) return
                      try {
                        await addSkillReview(skill.id, {
                          rating: Number(reviewRating),
                          comment: reviewComment,
                          tags: reviewTags.split(',').map((item) => item.trim()).filter(Boolean),
                        })
                        setReviews(await listSkillReviews(skill.id))
                        setReviewComment('')
                        setReviewTags('')
                        setMessage('评价已提交')
                      } catch (err: any) {
                        setMessage(err.response?.data?.detail || '提交评价失败')
                      }
                    }}
                  >
                    提交评价
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  )
}
