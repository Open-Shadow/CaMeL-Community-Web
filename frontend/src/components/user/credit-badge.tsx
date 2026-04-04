import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface CreditBadgeProps {
  level: string;
  score: number;
  showScore?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LEVEL_CONFIG: Record<string, { icon: string; name: string; color: string }> = {
  SEED: { icon: '🌱', name: '新芽', color: 'bg-green-100 text-green-800' },
  CRAFTSMAN: { icon: '🔧', name: '工匠', color: 'bg-blue-100 text-blue-800' },
  EXPERT: { icon: '⚡', name: '专家', color: 'bg-purple-100 text-purple-800' },
  MASTER: { icon: '🏆', name: '大师', color: 'bg-amber-100 text-amber-800' },
  GRANDMASTER: { icon: '👑', name: '宗师', color: 'bg-red-100 text-red-800' },
};

const LEVEL_THRESHOLDS = [
  { level: 'GRANDMASTER', min: 5000 },
  { level: 'MASTER', min: 2000 },
  { level: 'EXPERT', min: 500 },
  { level: 'CRAFTSMAN', min: 100 },
  { level: 'SEED', min: 0 },
];

export function CreditBadge({
  level,
  score,
  showScore = false,
  size = 'md',
  className,
}: CreditBadgeProps) {
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG.SEED;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-0.5',
    lg: 'text-base px-3 py-1',
  };

  return (
    <Badge
      className={cn(
        'font-medium',
        config.color,
        sizeClasses[size],
        className
      )}
    >
      <span className="mr-1">{config.icon}</span>
      {config.name}
      {showScore && <span className="ml-1 opacity-70">({score})</span>}
    </Badge>
  );
}

// 获取下一级所需分数
export function getNextLevelInfo(score: number): {
  currentLevel: string;
  nextLevel: string | null;
  progress: number;
  pointsNeeded: number;
} {
  const current = LEVEL_THRESHOLDS.find(t => score >= t.min) || LEVEL_THRESHOLDS[4];
  const currentIndex = LEVEL_THRESHOLDS.findIndex(t => t.level === current.level);
  const next = currentIndex > 0 ? LEVEL_THRESHOLDS[currentIndex - 1] : null;

  if (!next) {
    return {
      currentLevel: current.level,
      nextLevel: null,
      progress: 100,
      pointsNeeded: 0,
    };
  }

  const range = next.min - current.min;
  const progress = Math.min(100, Math.round(((score - current.min) / range) * 100));
  const pointsNeeded = next.min - score;

  return {
    currentLevel: current.level,
    nextLevel: next.level,
    progress,
    pointsNeeded,
  };
}

// 等级特权说明
export const LEVEL_PRIVILEGES: Record<string, string[]> = {
  SEED: ['发布免费 Skill', '发布 Workshop 文章'],
  CRAFTSMAN: ['发布付费 Skill', '参与投票', 'API 调用 95 折'],
  EXPERT: ['参与仲裁', 'API 调用 9 折'],
  MASTER: ['文章加精提名', 'API 调用 85 折'],
  GRANDMASTER: ['专属客服', 'API 调用 8 折'],
};
