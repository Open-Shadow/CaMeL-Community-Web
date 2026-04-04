import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  className?: string;
}

// Skill 卡片骨架
export function SkillCardSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 space-y-3",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-5 w-12" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      <div className="flex items-center gap-2 pt-2">
        <Skeleton className="h-8 w-8 rounded-full" />
        <Skeleton className="h-4 w-24" />
      </div>
      <div className="flex items-center justify-between pt-2">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  );
}

// Bounty 卡片骨架
export function BountyCardSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 space-y-3",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-5 w-16" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-4/5" />
      <div className="flex flex-wrap gap-2 pt-1">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
      </div>
      <div className="flex items-center justify-between pt-2 border-t">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  );
}

// 文章卡片骨架
export function ArticleCardSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 space-y-3",
        className
      )}
    >
      <div className="flex items-start gap-3">
        <Skeleton className="h-16 w-16 rounded-md shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-2">
          <Skeleton className="h-6 w-6 rounded-full" />
          <Skeleton className="h-3 w-16" />
        </div>
        <div className="flex items-center gap-3">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

// 通用列表骨架
interface ListSkeletonProps extends LoadingSkeletonProps {
  count?: number;
  itemHeight?: number;
}

export function ListSkeleton({
  count = 5,
  itemHeight = 60,
  className,
}: ListSkeletonProps) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton
          key={i}
          className="w-full"
          style={{ height: itemHeight }}
        />
      ))}
    </div>
  );
}

// 详情页骨架
export function DetailSkeleton({ className }: LoadingSkeletonProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <Skeleton className="h-8 w-3/4" />
      <div className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <div className="space-y-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
      <div className="pt-4 space-y-2">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

// 网格骨架
interface GridSkeletonProps extends LoadingSkeletonProps {
  count?: number;
  columns?: number;
}

export function GridSkeleton({
  count = 6,
  columns = 3,
  className,
}: GridSkeletonProps) {
  return (
    <div
      className={cn(
        "grid gap-4",
        {
          "grid-cols-1": columns === 1,
          "grid-cols-2": columns === 2,
          "grid-cols-3": columns === 3,
          "grid-cols-4": columns === 4,
          "grid-cols-5": columns === 5,
          "grid-cols-6": columns === 6,
        },
        className
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="aspect-[4/3]" />
      ))}
    </div>
  );
}
