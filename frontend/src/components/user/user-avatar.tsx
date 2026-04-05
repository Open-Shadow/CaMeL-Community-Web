import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { CreditBadge } from './credit-badge';

interface UserAvatarProps {
  name: string;
  avatarUrl?: string;
  level?: string;
  creditScore?: number;
  size?: 'sm' | 'md' | 'lg';
  showLevel?: boolean;
  showFrame?: boolean;
  className?: string;
}

// Level-based border/frame colors
const LEVEL_FRAME: Record<string, { border: string; glow: string }> = {
  SEED: { border: 'ring-gray-300', glow: '' },
  CRAFTSMAN: { border: 'ring-blue-400', glow: '' },
  EXPERT: { border: 'ring-purple-500', glow: 'shadow-[0_0_8px_rgba(168,85,247,0.4)]' },
  MASTER: { border: 'ring-amber-500', glow: 'shadow-[0_0_10px_rgba(245,158,11,0.5)]' },
  GRANDMASTER: { border: 'ring-red-500', glow: 'shadow-[0_0_12px_rgba(239,68,68,0.6)]' },
};

const VIP_LEVELS = new Set(['MASTER', 'GRANDMASTER']);

export function UserAvatar({
  name,
  avatarUrl,
  level,
  creditScore,
  size = 'md',
  showLevel = false,
  showFrame = true,
  className,
}: UserAvatarProps) {
  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-16 w-16 text-lg',
  };

  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const frame = level && showFrame ? LEVEL_FRAME[level] || LEVEL_FRAME.SEED : null;
  const isVip = level && VIP_LEVELS.has(level);

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="relative">
        <Avatar
          className={cn(
            sizeClasses[size],
            frame && 'ring-2',
            frame?.border,
            frame?.glow,
          )}
        >
          <AvatarImage src={avatarUrl} alt={name} />
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        {isVip && (
          <span
            className={cn(
              'absolute -top-1 -right-1 flex items-center justify-center rounded-full text-[10px] leading-none',
              size === 'sm' ? 'h-3.5 w-3.5' : size === 'lg' ? 'h-5 w-5 text-xs' : 'h-4 w-4',
              level === 'GRANDMASTER'
                ? 'bg-red-500 text-white'
                : 'bg-amber-500 text-white',
            )}
            title={level === 'GRANDMASTER' ? '宗师' : '大师'}
          >
            {level === 'GRANDMASTER' ? '👑' : '🏆'}
          </span>
        )}
      </div>
      <div className="flex flex-col">
        <span className="font-medium text-sm">{name}</span>
        {showLevel && level && (
          <CreditBadge level={level} score={creditScore || 0} size="sm" />
        )}
      </div>
    </div>
  );
}
