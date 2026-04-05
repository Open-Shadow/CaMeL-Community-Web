import { LogOut, Settings, User as UserIcon, Bell, Shield } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom'

import { NotificationBell } from '@/components/user/notification-bell';
import { BalanceDisplay } from '@/components/shared/balance-display';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/hooks/use-auth'
import { getInitials } from '@/lib/utils';

export function Header() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, logout, user } = useAuth()

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <header className="border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-16 items-center justify-between gap-6 px-4">
        <div className="flex items-center gap-8">
          <Link to="/" className="text-xl font-bold tracking-tight">CaMeL Community</Link>
          <nav className="hidden gap-6 text-sm text-muted-foreground md:flex">
            <Link to="/marketplace" className="transition hover:text-foreground">技能市场</Link>
            {isAuthenticated ? <Link to="/marketplace/mine" className="transition hover:text-foreground">我的 Skill</Link> : null}
            <Link to="/bounty" className="transition hover:text-foreground">悬赏任务</Link>
            <Link to="/workshop" className="transition hover:text-foreground">知识工坊</Link>
            <Link to="/rankings/credit" className="transition hover:text-foreground">排行榜</Link>
          </nav>
        </div>
        {isLoading ? (
          <div className="text-sm text-muted-foreground">加载中...</div>
        ) : isAuthenticated && user ? (
          <div className="flex items-center gap-3">
            <BalanceDisplay />
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="flex items-center gap-3 rounded-full border border-border bg-background px-2 py-1.5 transition hover:bg-accent"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatar_url} alt={user.display_name} />
                    <AvatarFallback>{getInitials(user.display_name || user.username)}</AvatarFallback>
                  </Avatar>
                  <div className="hidden text-left md:block">
                    <div className="text-sm font-medium leading-none">
                      {user.display_name || user.username}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">@{user.username}</div>
                  </div>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem asChild>
                  <Link to={`/u/${encodeURIComponent(user.username)}`} className="flex items-center gap-2">
                    <UserIcon className="h-4 w-4" />
                    公开主页
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/notifications" className="flex items-center gap-2">
                    <Bell className="h-4 w-4" />
                    通知中心
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/profile/settings" className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    个人设置
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link to="/profile/invites" className="flex items-center gap-2">
                    <UserIcon className="h-4 w-4" />
                    邀请中心
                  </Link>
                </DropdownMenuItem>
                {(user?.role === 'ADMIN' || user?.role === 'MODERATOR') && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link to="/admin" className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        管理后台
                      </Link>
                    </DropdownMenuItem>
                  </>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => void handleLogout()} className="flex items-center gap-2">
                  <LogOut className="h-4 w-4" />
                  退出登录
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost">
              <Link to="/login">登录</Link>
            </Button>
            <Button asChild>
              <Link to="/register">注册</Link>
            </Button>
          </div>
        )}
      </div>
    </header>
  )
}
