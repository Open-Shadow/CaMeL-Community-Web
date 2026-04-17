import { LogOut, Settings, User as UserIcon, Bell, Shield, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom'

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
import { cn, getInitials } from '@/lib/utils';

const NAV_LINKS = [
  { to: '/marketplace', label: '技能市场' },
  { to: '/bounty', label: '悬赏任务' },
  { to: '/workshop', label: '知识工坊' },
  { to: '/rankings/credit', label: '排行榜' },
];

export function Header() {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading, logout, user } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 border-b bg-white/80 backdrop-blur-lg">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-black text-white">C</span>
            <span className="hidden sm:inline">CaMeL</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
            {isAuthenticated ? (
              <NavLink
                to="/marketplace/mine"
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                我的 Skill
              </NavLink>
            ) : null}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {isLoading ? (
            <div className="h-8 w-20 animate-pulse rounded-md bg-muted" />
          ) : isAuthenticated && user ? (
            <>
              <BalanceDisplay />
              <NotificationBell />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    className="flex items-center gap-2 rounded-full p-1 transition hover:bg-muted"
                  >
                    <Avatar className="h-7 w-7">
                      <AvatarImage src={user.avatar_url} alt={user.display_name} />
                      <AvatarFallback className="text-xs">{getInitials(user.display_name || user.username)}</AvatarFallback>
                    </Avatar>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-52">
                  <div className="px-3 py-2">
                    <p className="text-sm font-medium">{user.display_name || user.username}</p>
                    <p className="text-xs text-muted-foreground">@{user.username}</p>
                  </div>
                  <DropdownMenuSeparator />
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
                  <DropdownMenuItem onClick={() => void handleLogout()} className="flex items-center gap-2 text-destructive">
                    <LogOut className="h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">登录</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/register">注册</Link>
              </Button>
            </>
          )}

          <button
            type="button"
            className="ml-1 rounded-md p-1.5 text-muted-foreground hover:bg-muted md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <nav className="border-t bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  )
}
