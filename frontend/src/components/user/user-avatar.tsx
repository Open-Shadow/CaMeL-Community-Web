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
  className?: string;
}

export function UserAvatar({
  name,
  avatarUrl,
  level,
  creditScore,
  size = 'md',
  showLevel = false,
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

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <Avatar className={sizeClasses[size]}>
        <AvatarImage src={avatarUrl} alt={name} />
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <div className="flex flex-col">
        <span className="font-medium text-sm">{name}</span>
        {showLevel && level && (
          <CreditBadge level={level} score={creditScore || 0} size="sm" />
        )}
      </div>
    </div>
  );
}
