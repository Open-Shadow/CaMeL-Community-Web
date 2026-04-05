import { ArrowDownRight, ArrowUpRight, History } from 'lucide-react';

import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { cn, formatDateTime, formatRelativeTime } from '@/lib/utils';

export interface CreditHistoryItem {
  id: number;
  action: string;
  amount: number;
  score_before: number;
  score_after: number;
  created_at: string;
}

interface CreditHistoryListProps {
  items: CreditHistoryItem[];
  total: number;
  isLoading?: boolean;
  compact?: boolean;
  onLoadMore?: () => void;
}

export function CreditHistoryList({
  items,
  total,
  isLoading = false,
  compact = false,
  onLoadMore,
}: CreditHistoryListProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: compact ? 3 : 6 }).map((_, index) => (
          <div
            key={index}
            className={cn(
              'animate-pulse rounded-2xl border bg-muted/40',
              compact ? 'h-20' : 'h-24'
            )}
          />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<History className="h-10 w-10" />}
        title="还没有信用分记录"
        description="后续发布内容、完成悬赏或触发奖励后，记录会出现在这里。"
        className="rounded-2xl border bg-muted/20"
      />
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const isPositive = item.amount >= 0;
        return (
          <div
            key={item.id}
            className={cn(
              'rounded-2xl border bg-white px-4 py-4 shadow-sm',
              compact ? 'py-3' : 'py-4'
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      'inline-flex h-8 w-8 items-center justify-center rounded-full',
                      isPositive ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
                    )}
                  >
                    {isPositive ? (
                      <ArrowUpRight className="h-4 w-4" />
                    ) : (
                      <ArrowDownRight className="h-4 w-4" />
                    )}
                  </span>
                  <div>
                    <p className="font-medium text-foreground">{item.action}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatRelativeTime(item.created_at)} · {formatDateTime(item.created_at)}
                    </p>
                  </div>
                </div>
                <p className="pl-10 text-sm text-muted-foreground">
                  分数变化：{item.score_before} → {item.score_after}
                </p>
              </div>
              <div
                className={cn(
                  'rounded-full px-3 py-1 text-sm font-semibold',
                  isPositive ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                )}
              >
                {isPositive ? '+' : ''}
                {item.amount}
              </div>
            </div>
          </div>
        );
      })}

      {items.length < total && onLoadMore ? (
        <div className="flex justify-center pt-2">
          <Button variant="outline" onClick={onLoadMore}>
            加载更多
          </Button>
        </div>
      ) : null}
    </div>
  );
}
