import { ThumbsDown, ThumbsUp, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'

interface VoteButtonsProps {
  netVotes: number
  myVote: 'UP' | 'DOWN' | null
  disabled?: boolean
  onVote: (value: 'UP' | 'DOWN') => void
  onRemove: () => void
}

export function VoteButtons({ netVotes, myVote, disabled = false, onVote, onRemove }: VoteButtonsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-3">
      <Button
        type="button"
        variant={myVote === 'UP' ? 'default' : 'outline'}
        disabled={disabled}
        onClick={() => onVote('UP')}
      >
        <ThumbsUp className="mr-2 h-4 w-4" />
        有用
      </Button>
      <Button
        type="button"
        variant={myVote === 'DOWN' ? 'default' : 'outline'}
        disabled={disabled}
        onClick={() => onVote('DOWN')}
      >
        <ThumbsDown className="mr-2 h-4 w-4" />
        无用
      </Button>
      <div className="min-w-24 text-sm font-medium text-foreground">净票 {netVotes.toFixed(1)}</div>
      {myVote ? (
        <Button type="button" variant="ghost" disabled={disabled} onClick={onRemove}>
          <Trash2 className="mr-2 h-4 w-4" />
          取消投票
        </Button>
      ) : null}
    </div>
  )
}
