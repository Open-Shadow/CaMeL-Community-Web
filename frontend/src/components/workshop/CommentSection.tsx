import { useState } from 'react'
import { ChevronDown, ChevronUp, MessageSquareReply, Pin, ThumbsDown, ThumbsUp } from 'lucide-react'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { ArticleComment, ArticleCommentReply } from '@/lib/workshop'
import { cn, formatRelativeTime, getInitials } from '@/lib/utils'

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

const LEVEL_LABELS: Record<string, string> = {
  SEED: '🌱 新芽',
  CRAFTSMAN: '🔧 工匠',
  EXPERT: '⚡ 专家',
  MASTER: '🏆 大师',
  GRANDMASTER: '👑 宗师',
}

function CommentComposer({
  placeholder,
  buttonText,
  submitting,
  autoFocus,
  onSubmit,
  onCancel,
}: {
  placeholder: string
  buttonText: string
  submitting: boolean
  autoFocus?: boolean
  onSubmit: (content: string) => Promise<void>
  onCancel?: () => void
}) {
  const [content, setContent] = useState('')
  const [focused, setFocused] = useState(false)

  const expanded = focused || content.length > 0

  return (
    <div className="space-y-2">
      <Textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        onFocus={() => setFocused(true)}
        rows={expanded ? 3 : 1}
        placeholder={placeholder}
        autoFocus={autoFocus}
        className={cn(
          'resize-none transition-all',
          !expanded && 'min-h-[40px] rounded-full bg-muted/50 px-4 py-2',
        )}
      />
      {expanded && (
        <div className="flex items-center justify-end gap-2">
          {onCancel && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setContent('')
                setFocused(false)
                onCancel()
              }}
            >
              取消
            </Button>
          )}
          <Button
            type="button"
            size="sm"
            disabled={submitting || !content.trim()}
            onClick={async () => {
              await onSubmit(content)
              setContent('')
              setFocused(false)
            }}
          >
            {buttonText}
          </Button>
        </div>
      )}
    </div>
  )
}

function CommentActions({
  comment,
  isAuthenticated,
  canPin,
  canReply,
  onVote,
  onRemoveVote,
  onReply,
  onPin,
}: {
  comment: ArticleCommentReply
  isAuthenticated: boolean
  canPin?: boolean
  canReply?: boolean
  onVote: (commentId: number, value: 'UP' | 'DOWN') => Promise<void>
  onRemoveVote: (commentId: number) => Promise<void>
  onReply?: () => void
  onPin?: (commentId: number) => Promise<void>
}) {
  return (
    <div className="flex items-center gap-1 text-muted-foreground">
      {isAuthenticated ? (
        <>
          <button
            type="button"
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors hover:bg-muted',
              comment.my_vote === 'UP' && 'text-primary',
            )}
            onClick={() => (comment.my_vote === 'UP' ? onRemoveVote(comment.id) : onVote(comment.id, 'UP'))}
          >
            <ThumbsUp className="h-3.5 w-3.5" />
            {comment.net_votes > 0 && <span>{comment.net_votes}</span>}
          </button>
          <button
            type="button"
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors hover:bg-muted',
              comment.my_vote === 'DOWN' && 'text-destructive',
            )}
            onClick={() => (comment.my_vote === 'DOWN' ? onRemoveVote(comment.id) : onVote(comment.id, 'DOWN'))}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
          {canReply && (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors hover:bg-muted"
              onClick={onReply}
            >
              <MessageSquareReply className="h-3.5 w-3.5" />
              回复
            </button>
          )}
          {canPin && onPin && (
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors hover:bg-muted"
              onClick={() => onPin(comment.id)}
            >
              <Pin className="h-3.5 w-3.5" />
              {comment.is_pinned ? '取消置顶' : '置顶'}
            </button>
          )}
        </>
      ) : (
        comment.net_votes !== 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs">
            <ThumbsUp className="h-3.5 w-3.5" />
            {comment.net_votes}
          </span>
        )
      )}
    </div>
  )
}

function ReplyItem({
  reply,
  isAuthenticated,
  onVote,
  onRemoveVote,
}: {
  reply: ArticleCommentReply
  isAuthenticated: boolean
  onVote: (commentId: number, value: 'UP' | 'DOWN') => Promise<void>
  onRemoveVote: (commentId: number) => Promise<void>
}) {
  if (reply.is_collapsed) {
    return (
      <div className="flex gap-3 py-2">
        <Avatar className="h-6 w-6 shrink-0">
          <AvatarImage src={reply.author.avatar_url || undefined} alt={reply.author.display_name} />
          <AvatarFallback className="text-[10px]">{getInitials(reply.author.display_name)}</AvatarFallback>
        </Avatar>
        <span className="text-xs text-muted-foreground italic">该回复因低分被折叠</span>
      </div>
    )
  }

  return (
    <div className="flex gap-3 py-2">
      <Avatar className="h-6 w-6 shrink-0">
        <AvatarImage src={reply.author.avatar_url || undefined} alt={reply.author.display_name} />
        <AvatarFallback className="text-[10px]">{getInitials(reply.author.display_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="text-[13px] font-medium">{reply.author.display_name}</span>
          <span className="text-xs text-muted-foreground">{formatRelativeTime(reply.created_at)}</span>
        </div>
        <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{reply.content}</p>
        <div className="mt-1">
          <CommentActions
            comment={reply}
            isAuthenticated={isAuthenticated}
            onVote={onVote}
            onRemoveVote={onRemoveVote}
          />
        </div>
      </div>
    </div>
  )
}

function CommentItem({
  comment,
  canPin,
  isAuthenticated,
  submitting,
  replyOpen,
  onToggleReply,
  onSubmit,
  onPin,
  onVote,
  onRemoveVote,
}: {
  comment: ArticleComment
  canPin: boolean
  isAuthenticated: boolean
  submitting: boolean
  replyOpen: boolean
  onToggleReply: () => void
  onSubmit: (content: string, parentId?: number) => Promise<void>
  onPin: (commentId: number) => Promise<void>
  onVote: (commentId: number, value: 'UP' | 'DOWN') => Promise<void>
  onRemoveVote: (commentId: number) => Promise<void>
}) {
  const [repliesExpanded, setRepliesExpanded] = useState(false)
  const [collapsed, setCollapsed] = useState(comment.is_collapsed)

  return (
    <div className="flex gap-3 py-4">
      <Avatar className="h-10 w-10 shrink-0">
        <AvatarImage src={comment.author.avatar_url || undefined} alt={comment.author.display_name} />
        <AvatarFallback>{getInitials(comment.author.display_name)}</AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium">{comment.author.display_name}</span>
          <span className="text-xs text-muted-foreground">
            {LEVEL_LABELS[comment.author.level] || comment.author.level}
          </span>
          <span className="text-xs text-muted-foreground">{formatRelativeTime(comment.created_at)}</span>
          {comment.is_pinned && (
            <span className="inline-flex items-center gap-0.5 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              <Pin className="h-2.5 w-2.5" />
              置顶
            </span>
          )}
        </div>

        {collapsed ? (
          <button
            type="button"
            className="mt-1 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => setCollapsed(false)}
          >
            该评论因低分被折叠，点击展开
          </button>
        ) : (
          <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{comment.content}</p>
        )}

        <div className="mt-1">
          <CommentActions
            comment={comment}
            isAuthenticated={isAuthenticated}
            canPin={canPin}
            canReply
            onVote={onVote}
            onRemoveVote={onRemoveVote}
            onReply={onToggleReply}
            onPin={onPin}
          />
        </div>

        {replyOpen && (
          <div className="mt-3">
            <CommentComposer
              placeholder={`回复 @${comment.author.display_name}...`}
              buttonText="回复"
              submitting={submitting}
              autoFocus
              onSubmit={async (content) => {
                await onSubmit(content, comment.id)
              }}
              onCancel={onToggleReply}
            />
          </div>
        )}

        {comment.replies.length > 0 && (
          <div className="mt-2">
            {!repliesExpanded ? (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/5"
                onClick={() => setRepliesExpanded(true)}
              >
                <ChevronDown className="h-3.5 w-3.5" />
                展开 {comment.replies.length} 条回复
              </button>
            ) : (
              <>
                <div className="border-l-2 border-muted pl-2">
                  {comment.replies.map((reply) => (
                    <ReplyItem
                      key={reply.id}
                      reply={reply}
                      isAuthenticated={isAuthenticated}
                      onVote={onVote}
                      onRemoveVote={onRemoveVote}
                    />
                  ))}
                </div>
                <button
                  type="button"
                  className="mt-1 inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/5"
                  onClick={() => setRepliesExpanded(false)}
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                  收起回复
                </button>
              </>
            )}
          </div>
        )}
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
  const [replyTo, setReplyTo] = useState<number | null>(null)

  const totalCount = comments.reduce((sum, c) => sum + 1 + c.replies.length, 0)

  return (
    <div className="space-y-4">
      <div className="flex items-baseline gap-3">
        <h3 className="text-lg font-semibold">{totalCount} 条评论</h3>
      </div>

      {isAuthenticated ? (
        <CommentComposer
          placeholder="添加评论..."
          buttonText="评论"
          submitting={submitting}
          onSubmit={(content) => onSubmit(content)}
        />
      ) : (
        <div className="rounded-full bg-muted/50 px-4 py-2.5 text-sm text-muted-foreground">
          登录后可发表评论与回复
        </div>
      )}

      <div className="divide-y">
        {comments.map((comment) => (
          <CommentItem
            key={comment.id}
            comment={comment}
            canPin={canPin}
            isAuthenticated={isAuthenticated}
            submitting={submitting}
            replyOpen={replyTo === comment.id}
            onToggleReply={() => setReplyTo((current) => (current === comment.id ? null : comment.id))}
            onSubmit={async (content, parentId) => {
              await onSubmit(content, parentId)
              setReplyTo(null)
            }}
            onPin={onPin}
            onVote={onVote}
            onRemoveVote={onRemoveVote}
          />
        ))}
      </div>

      {comments.length === 0 && (
        <div className="py-10 text-center text-sm text-muted-foreground">
          还没有评论，来留下第一条吧
        </div>
      )}
    </div>
  )
}
