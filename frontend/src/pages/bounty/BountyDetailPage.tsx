import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { BountyTimeline } from '@/components/bounty/BountyTimeline'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/hooks/use-auth'
import {
  acceptBountyApplication,
  addBountyReview,
  addBountyComment,
  appealArbitration,
  applyBounty,
  approveBounty,
  castArbitrationVote,
  createBountyDispute,
  getBounty,
  requestBountyRevision,
  startArbitration,
  submitArbitrationStatement,
  submitBountyDelivery,
  type BountyDetail,
} from '@/lib/bounties'
import { formatCurrency, formatDateTime } from '@/lib/utils'

const WORKLOAD_LABELS: Record<string, string> = {
  ONE_TO_TWO_HOURS: '1~2小时',
  HALF_DAY: '半天',
  ONE_DAY: '1天',
  TWO_TO_THREE_DAYS: '2~3天',
  ONE_WEEK_PLUS: '1周以上',
}

export default function BountyDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()

  const [data, setData] = useState<BountyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [proposal, setProposal] = useState('')
  const [estimatedDays, setEstimatedDays] = useState('3')
  const [comment, setComment] = useState('')
  const [deliverable, setDeliverable] = useState('')
  const [revisionFeedback, setRevisionFeedback] = useState('')
  const [statement, setStatement] = useState('')
  const [appealReason, setAppealReason] = useState('')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewScore, setReviewScore] = useState('5')

  const load = async () => {
    if (!id) return
    setLoading(true)
    setError('')
    try {
      setData(await getBounty(Number(id)))
    } catch (loadError: any) {
      setError(loadError.response?.data?.message || '悬赏详情加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [id])

  const acceptedUserId = data?.accepted_applicant?.id
  const isCreator = data?.creator.id === user?.id
  const isHunter = acceptedUserId === user?.id
  const isArbitrator = useMemo(
    () => Boolean(data?.arbitration?.arbitrators.some((item) => item.id === user?.id)),
    [data?.arbitration?.arbitrators, user?.id],
  )

  if (loading) {
    return <div className="py-12 text-center text-muted-foreground">加载悬赏详情中...</div>
  }

  if (error || !data) {
    return (
      <EmptyState
        title="悬赏详情不可用"
        description={error || '未找到对应悬赏'}
        action={<Button onClick={() => navigate('/bounty')}>返回列表</Button>}
      />
    )
  }

  const perform = async (handler: () => Promise<BountyDetail | void>) => {
    try {
      const next = await handler()
      if (next) setData(next)
      else await load()
      setError('')
    } catch (actionError: any) {
      setError(actionError.response?.data?.message || '操作失败')
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" onClick={() => navigate('/bounty')}>← 返回悬赏列表</Button>
        <Badge variant="outline">{data.status}</Badge>
      </div>

      <section className="rounded-2xl border bg-card p-6 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">{data.title}</h1>
          <span className="text-xl font-semibold text-primary">{formatCurrency(data.reward)}</span>
        </div>
        <p className="mb-4 max-w-3xl text-sm leading-7 text-muted-foreground">{data.description}</p>
        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
          <span>发布者 {data.creator.display_name}</span>
          <span>申请数 {data.application_count}</span>
          <span>申请上限 {data.max_applicants}</span>
          <span>截止 {formatDateTime(data.deadline)}</span>
          <span>修改轮次 {data.revision_count}/3</span>
          {data.workload_estimate ? (
            <span>预计工作量 {WORKLOAD_LABELS[data.workload_estimate] || data.workload_estimate}</span>
          ) : null}
        </div>

        {data.skill_requirements ? (
          <div className="mt-4 rounded-xl border bg-muted/30 p-4 text-sm">
            <div className="mb-2 font-medium">技能要求</div>
            <p className="whitespace-pre-wrap text-muted-foreground">{data.skill_requirements}</p>
          </div>
        ) : null}

        {data.attachments.length > 0 ? (
          <div className="mt-4 rounded-xl border bg-muted/30 p-4 text-sm">
            <div className="mb-2 font-medium">附件</div>
            <div className="space-y-2">
              {data.attachments.map((item) => (
                <a
                  key={item}
                  href={item}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-primary hover:underline break-all"
                >
                  {item}
                </a>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      {error ? <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div> : null}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>状态时间线</CardTitle>
            </CardHeader>
            <CardContent><BountyTimeline status={data.status} /></CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>申请列表</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.applications.length === 0 ? (
                <p className="text-sm text-muted-foreground">暂时还没有申请。</p>
              ) : (
                data.applications.map((application) => (
                  <div key={application.id} className="rounded-xl border p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-medium">{application.applicant.display_name}</div>
                        <div className="text-xs text-muted-foreground">
                          预计 {application.estimated_days} 天 · {formatDateTime(application.created_at)}
                        </div>
                      </div>
                      {isCreator && data.status === 'OPEN' ? (
                        <Button size="sm" onClick={() => void perform(() => acceptBountyApplication(data.id, application.id))}>
                          接受申请
                        </Button>
                      ) : null}
                    </div>
                    <p className="mt-3 text-sm text-muted-foreground">{application.proposal}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>沟通记录</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.comments.length === 0 ? <p className="text-sm text-muted-foreground">还没有沟通记录。</p> : null}
              {data.comments.map((item) => (
                <div key={item.id} className="rounded-xl border p-4">
                  <div className="text-sm font-medium">{item.author.display_name}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{formatDateTime(item.created_at)}</div>
                  <p className="mt-3 text-sm text-muted-foreground">{item.content}</p>
                </div>
              ))}
              {isAuthenticated ? (
                <div className="space-y-3 border-t pt-4">
                  <Textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="补充沟通信息..." rows={3} />
                  <Button
                    onClick={() =>
                      void perform(async () => {
                        await addBountyComment(data.id, comment)
                        setComment('')
                      })}
                    disabled={!comment.trim()}
                  >
                    发送评论
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {data.deliverables.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>交付记录</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.deliverables.map((item) => (
                  <div key={item.id} className="rounded-xl border p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium">第 {item.revision_number} 次交付</div>
                      <div className="text-xs text-muted-foreground">{formatDateTime(item.created_at)}</div>
                    </div>
                    <p className="mt-3 text-sm text-muted-foreground">{item.content}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {data.reviews.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>双方互评</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.reviews.map((review) => (
                  <div key={review.id} className="rounded-xl border p-4 text-sm">
                    <div className="font-medium">
                      {review.reviewer.display_name} → {review.reviewee.display_name}
                    </div>
                    <div className="mt-2 text-muted-foreground">
                      质量 {review.quality_rating} / 沟通 {review.communication_rating} / 响应 {review.responsiveness_rating}
                    </div>
                    {review.comment ? <p className="mt-2 text-muted-foreground">{review.comment}</p> : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </div>

        <div className="space-y-6">
          {data.status === 'OPEN' && isAuthenticated && !isCreator ? (
            <Card>
              <CardHeader>
                <CardTitle>申请接单</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea value={proposal} onChange={(event) => setProposal(event.target.value)} placeholder="简述你的方案和经验..." rows={4} />
                <Input value={estimatedDays} onChange={(event) => setEstimatedDays(event.target.value)} type="number" min="1" />
                <Button
                  className="w-full"
                  disabled={!proposal.trim()}
                  onClick={() =>
                    void perform(async () => {
                      await applyBounty(data.id, { proposal, estimated_days: Number(estimatedDays) || 1 })
                      setProposal('')
                    })}
                >
                  提交申请
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {isHunter && ['IN_PROGRESS', 'REVISION'].includes(data.status) ? (
            <Card>
              <CardHeader>
                <CardTitle>提交交付</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea value={deliverable} onChange={(event) => setDeliverable(event.target.value)} placeholder="描述交付内容、链接或结果..." rows={5} />
                <Button
                  className="w-full"
                  disabled={!deliverable.trim()}
                  onClick={() =>
                    void perform(async () => {
                      const next = await submitBountyDelivery(data.id, { content: deliverable })
                      setDeliverable('')
                      return next
                    })}
                >
                  提交交付
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {isCreator && ['DELIVERED', 'IN_REVIEW'].includes(data.status) ? (
            <Card>
              <CardHeader>
                <CardTitle>验收操作</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={revisionFeedback}
                  onChange={(event) => setRevisionFeedback(event.target.value)}
                  placeholder="如需修改，写清楚验收意见..."
                  rows={4}
                />
                <div className="grid gap-2">
                  <Button onClick={() => void perform(() => approveBounty(data.id))}>验收通过</Button>
                  <Button variant="outline" onClick={() => void perform(() => requestBountyRevision(data.id, revisionFeedback))}>
                    要求修改
                  </Button>
                  <Button variant="destructive" onClick={() => void perform(() => createBountyDispute(data.id, revisionFeedback || '发布者拒绝验收，发起争议'))}>
                    发起争议
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {data.arbitration ? (
            <Card>
              <CardHeader>
                <CardTitle>争议仲裁</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-sm text-muted-foreground">
                  冷静期截止：{data.arbitration.deadline ? formatDateTime(data.arbitration.deadline) : '未开始'}
                </div>
                <div className="space-y-2 text-sm">
                  <div>发布者陈述：{data.arbitration.creator_statement || '暂无'}</div>
                  <div>接单者陈述：{data.arbitration.hunter_statement || '暂无'}</div>
                </div>

                {(isCreator || isHunter) ? (
                  <div className="space-y-2">
                    <Textarea value={statement} onChange={(event) => setStatement(event.target.value)} placeholder="补充争议陈述..." rows={3} />
                    <Button variant="outline" disabled={!statement.trim()} onClick={() => void perform(() => submitArbitrationStatement(data.id, statement))}>
                      提交陈述
                    </Button>
                  </div>
                ) : null}

                {isCreator && data.status === 'DISPUTED' ? (
                  <Button onClick={() => void perform(() => startArbitration(data.id))}>冷静期后启动仲裁</Button>
                ) : null}

                {isArbitrator && data.status === 'ARBITRATING' ? (
                  <div className="grid gap-2">
                    <Button variant="outline" onClick={() => void perform(() => castArbitrationVote(data.id, { vote: 'CREATOR_WIN' }))}>
                      投票支持发布者
                    </Button>
                    <Button variant="outline" onClick={() => void perform(() => castArbitrationVote(data.id, { vote: 'HUNTER_WIN' }))}>
                      投票支持接单者
                    </Button>
                    <Button variant="outline" onClick={() => void perform(() => castArbitrationVote(data.id, { vote: 'PARTIAL', hunter_ratio: 0.5 }))}>
                      部分完成 50%
                    </Button>
                  </div>
                ) : null}

                {data.arbitration.resolved_at ? (
                  <div className="space-y-2 rounded-xl border bg-muted/30 p-4 text-sm">
                    <div>结果：{data.arbitration.result}</div>
                    <div>接单者比例：{data.arbitration.hunter_ratio ?? 0}</div>
                    <div>结案时间：{formatDateTime(data.arbitration.resolved_at)}</div>
                    {(isCreator || isHunter) ? (
                      <>
                        <Textarea value={appealReason} onChange={(event) => setAppealReason(event.target.value)} placeholder="如需上诉，说明理由..." rows={3} />
                        <Button variant="outline" onClick={() => void perform(() => appealArbitration(data.id, appealReason))}>
                          提交上诉
                        </Button>
                      </>
                    ) : null}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {(isCreator || isHunter) && ['COMPLETED', 'CANCELLED'].includes(data.status) ? (
            <Card>
              <CardHeader>
                <CardTitle>提交互评</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Input
                  type="number"
                  min="1"
                  max="5"
                  value={reviewScore}
                  onChange={(event) => setReviewScore(event.target.value)}
                />
                <Textarea
                  value={reviewComment}
                  onChange={(event) => setReviewComment(event.target.value)}
                  placeholder="评价质量、沟通和响应速度..."
                  rows={3}
                />
                <Button
                  onClick={() =>
                    void perform(async () => addBountyReview(data.id, {
                      quality_rating: Number(reviewScore),
                      communication_rating: Number(reviewScore),
                      responsiveness_rating: Number(reviewScore),
                      comment: reviewComment,
                    }))
                  }
                >
                  提交互评
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  )
}
