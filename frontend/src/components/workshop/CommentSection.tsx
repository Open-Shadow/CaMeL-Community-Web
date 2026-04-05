import { useState } from 'react'
import { ChevronDown, MessageSquareReply, Pin, ThumbsDown, ThumbsUp } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import type { ArticleComment } from '@/lib/workshop'
import { formatDate } from '@/lib/utils'

interface CommentSectionProps {
  comments: ArticleComment[]
  canPin: boolean
  isAuthenticated: boolean
  submitting: boolean
  onSubmit: (content: string, parentId?: number) => Promise<void>
  onPin: (commentId: number) => Promise<void>
  onVote: (commentId: number, value: 'UP' | 'DOWN') => Promise<void>
  onRemoveVote: (commentId: number) => Promise<void>
}

function ReplyComposer({
  submitting,
  onSubmit,
}: {
  submitting: boolean
  onSubmit: (content: string) => Promise<void>
}) {
  const [content, setContent] = useState('')

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-dashed p-3">
      <Textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        rows={3}
        placeholder="补充你的回复..."
      />
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          disabled={submitting || !content.trim()}
          onClick={async () => {
            await onSubmit(content)
            setContent('')
          }}
        >
          回复
        </Button>
      </div>
    </div>
  )
}

export function CommentSection({
  comments,
  canPin,
  isAuthenticated,
  submitting,
  onSubmit,
  onPin,
  onVote,
  onRemoveVote,
}: CommentSectionProps) {
  const [draft, setDraft] = useState('')
  const [replyTo, setReplyTo] = useState<number | null>(null)
  const [expandedCollapsed, setExpandedCollapsed] = useState<Record<number, boolean>>({})

  return (
    <div className="space-y-5">
      <div className="space-y-3 rounded-2xl border bg-white p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">评论区</h3>
          <span className="text-sm text-muted-foreground">{comments.length} 条主评论</span>
        </div>
        {isAuthenticated ? (
          <>
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              rows={4}
              placeholder="分享你的补充、纠错或实践结果..."
            />
            <div className="flex justify-end">
              <Button
                type="button"
                disabled={submitting || !draft.trim()}
                onClick={async () => {
                  await onSubmit(draft)
                  setDraft('')
                }}
              >
                发表评论
              </Button>
            </div>
          </>
        ) : (
          <div className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            登录后可发表评论与回复。
          </div>
        )}
      </div>

      {comments.length === 0 ? (
        <div className="rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          还没有评论，先留下第一条反馈。
        </div>
      ) : (
        comments.map((comment) => (
          <Card key={comment.id} className={comment.is_pinned ? 'border-amber-300 shadow-sm' : undefined}>
            <CardContent className="space-y-4 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-slate-900">{comment.author.display_name}</div>
                  <div className="text-xs text-muted-foreground">
                    {comment.author.level} · {formatDate(comment.created_at)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {comment.is_pinned ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs text-amber-800">
                      <Pin className="h-3 w-3" />
                      置顶
                    </span>
                  ) : null}
                  {canPin ? (
                    <Button type="button" variant="ghost" size="sm" onClick={() => onPin(comment.id)}>
                      置顶
                    </Button>
                  ) : null}
                </div>
              </div>

              {comment.is_collapsed && !expandedCollapsed[comment.id] ? (
                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground"
                  onClick={() => setExpandedCollapsed((current) => ({ ...current, [comment.id]: true }))}
                >
                  <ChevronDown className="h-3 w-3" />
                  该评论因低分被折叠，点击展开
                </button>
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{comment.content}</p>
              )}

              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>净票 {comment.net_votes}</span>
                <div className="flex items-center gap-1">
                  {isAuthenticated ? (
                    <>
                      <Button
                        type="button"
                        variant={comment.my_vote === 'UP' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => (comment.my_vote === 'UP' ? onRemoveVote(comment.id) : onVote(comment.id, 'UP'))}
                      >
                        <ThumbsUp className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        variant={comment.my_vote === 'DOWN' ? 'destructive' : 'ghost'}
                        size="sm"
                        onClick={() => (comment.my_vote === 'DOWN' ? onRemoveVote(comment.id) : onVote(comment.id, 'DOWN'))}
                      >
                        <ThumbsDown className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setReplyTo((current) => (current === comment.id ? null : comment.id))}
                      >
                        <MessageSquareReply className="mr-1 h-4 w-4" />
                        回复
                      </Button>
                    </>
                  ) : null}
                </div>
              </div>

              {replyTo === comment.id ? (
                <ReplyComposer
                  submitting={submitting}
                  onSubmit={async (content) => {
                    await onSubmit(content, comment.id)
                    setReplyTo(null)
                  }}
                />
              ) : null}

              {comment.replies.length > 0 ? (
                <div className="space-y-3 rounded-xl bg-slate-50 p-4">
                  {comment.replies.map((reply) => (
                    <div key={reply.id} className="rounded-lg border bg-white p-3">
                      <div className="mb-1 text-sm font-medium text-slate-900">
                        {reply.author.display_name}
                      </div>
                      <div className="mb-2 text-xs text-muted-foreground">
                        {reply.author.level} · {formatDate(reply.created_at)}
                      </div>
                      {reply.is_collapsed ? (
                        <div className="text-xs text-muted-foreground">该回复因低分被折叠</div>
                      ) : (
                        <p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{reply.content}</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}
