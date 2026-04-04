interface UserAvatarProps {
  username: string
  avatarUrl?: string
  size?: 'sm' | 'md' | 'lg'
}

export function UserAvatar({ username, avatarUrl, size = 'md' }: UserAvatarProps) {
  const sizeClasses = {
    sm: 'w-6 h-6 text-xs',
    md: 'w-8 h-8 text-sm',
    lg: 'w-12 h-12 text-base',
  }

  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        className={`${sizeClasses[size]} rounded-full object-cover`}
      />
    )
  }

  const initials = username.slice(0, 2).toUpperCase()
  return (
    <div
      className={`${sizeClasses[size]} rounded-full bg-gray-200 flex items-center justify-center font-medium`}
    >
      {initials}
    </div>
  )
}
